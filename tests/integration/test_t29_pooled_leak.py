from __future__ import annotations

import os
import random
from collections.abc import Callable
from uuid import UUID

import psycopg
import pytest
from cleartrace_db.session import tenant_transaction
from uuid6 import uuid7

pytestmark = [pytest.mark.integration, pytest.mark.trl5]

TENANT_A = UUID("11111111-1111-7111-8111-111111111101")
TENANT_B = UUID("11111111-1111-7111-8111-111111111102")
TENANT_C = UUID("11111111-1111-7111-8111-111111111103")
TENANTS = (TENANT_A, TENANT_B, TENANT_C)

TRANSACTION_COUNT = 1000


def _dsn() -> str:
    return os.environ.get(
        "CLEARTRACE_TEST_DSN",
        "postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace",
    )


@pytest.fixture(scope="module", autouse=True)
def seed_tenant_markers(dsn: str) -> None:
    for tenant_id, marker in (
        (TENANT_A, "MARKER-A"),
        (TENANT_B, "MARKER-B"),
        (TENANT_C, "MARKER-C"),
    ):
        with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_system (id, tenant_id, system_key)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (uuid7(), tenant_id, marker),
            )


@pytest.fixture(scope="module")
def dsn() -> str:
    return _dsn()


class _PlannedRollback(Exception):
    """Raised on purpose to roll a transaction back mid-way."""


def test_t29_zero_cross_tenant_leaks_over_pooled_connections(
    dsn: str, record_property: Callable[[str, object], None]
) -> None:
    """T-29: 0 leaks in 1,000 mixed transactions over PgBouncer (10,000 deferred).

    The mix covers committed reads and writes, transactions rolled back after a write,
    and savepoints that try to write another tenant's row. Server backend PIDs are
    recorded to show that PgBouncer really hands the same server connections to
    different tenants.
    """
    leaks = 0
    rng = random.Random(29)
    backend_tenants: dict[int, set[UUID]] = {}
    rolled_back: list[tuple[UUID, UUID]] = []
    foreign_inserts_blocked = 0
    for step in range(TRANSACTION_COUNT):
        tenant_id = TENANTS[step % len(TENANTS)]
        other_tenant = TENANTS[(step + 1) % len(TENANTS)]
        expected_marker = {TENANT_A: "MARKER-A", TENANT_B: "MARKER-B", TENANT_C: "MARKER-C"}[
            tenant_id
        ]
        with (
            psycopg.connect(dsn, autocommit=False, prepare_threshold=None) as raw_conn,
            raw_conn.cursor() as cur,
        ):
            cur.execute("SELECT current_setting('app.tenant_id', true)")
            stale = cur.fetchone()
            if stale and stale[0]:
                leaks += 1
            # Without tenant context RLS must hide every row.
            cur.execute("SELECT count(*) FROM ai_system")
            visible = cur.fetchone()
            if visible and int(visible[0]) > 0:
                leaks += 1
        planned_rollback = step % 7 == 3
        probe = uuid7()
        try:
            with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
                cur.execute("SELECT pg_backend_pid()")
                pid_row = cur.fetchone()
                if pid_row is not None:
                    backend_tenants.setdefault(int(pid_row[0]), set()).add(tenant_id)
                cur.execute("SELECT current_setting('app.tenant_id', true)")
                setting_row = cur.fetchone()
                if setting_row is None or str(setting_row[0]) != str(tenant_id):
                    leaks += 1
                cur.execute("SELECT system_key, tenant_id FROM ai_system ORDER BY system_key")
                for system_key, row_tid in cur.fetchall():
                    if row_tid != tenant_id:
                        leaks += 1
                    if system_key == expected_marker and row_tid != tenant_id:
                        leaks += 1
                cur.execute(
                    "INSERT INTO ai_system (id, tenant_id, system_key) VALUES (%s, %s, %s)",
                    (probe, tenant_id, f"TMP-{step}-{rng.randint(0, 9999)}"),
                )
                if step % 5 == 1:
                    # RLS must refuse a row for another tenant; the savepoint keeps the
                    # rest of the transaction usable.
                    try:
                        with conn.transaction():
                            cur.execute(
                                "INSERT INTO ai_system (id, tenant_id, system_key)"
                                " VALUES (%s, %s, %s)",
                                (uuid7(), other_tenant, f"FOREIGN-{step}"),
                            )
                        leaks += 1
                    except psycopg.errors.InsufficientPrivilege:
                        foreign_inserts_blocked += 1
                cur.execute(
                    "SELECT count(*) FROM ai_system WHERE tenant_id <> %s",
                    (tenant_id,),
                )
                foreign = cur.fetchone()
                if foreign and int(foreign[0]) > 0:
                    leaks += 1
                if planned_rollback:
                    raise _PlannedRollback
        except _PlannedRollback:
            rolled_back.append((tenant_id, probe))

    # Rolled-back writes must not exist for anyone, and no FOREIGN row may exist at all.
    for tenant_id in TENANTS:
        with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
            own_probes = [p for t, p in rolled_back if t == tenant_id]
            cur.execute("SELECT count(*) FROM ai_system WHERE id = ANY(%s)", (own_probes,))
            survived = cur.fetchone()
            if survived and int(survived[0]) > 0:
                leaks += int(survived[0])
            cur.execute("SELECT count(*) FROM ai_system WHERE system_key LIKE 'FOREIGN-%%'")
            foreign_rows = cur.fetchone()
            if foreign_rows and int(foreign_rows[0]) > 0:
                leaks += int(foreign_rows[0])

    shared_backends = sum(1 for tenants in backend_tenants.values() if len(tenants) > 1)
    record_property("t29_transactions", TRANSACTION_COUNT)
    record_property("t29_distinct_backends", len(backend_tenants))
    record_property("t29_backends_shared_by_tenants", shared_backends)
    record_property("t29_rolled_back", len(rolled_back))
    record_property("t29_foreign_inserts_blocked", foreign_inserts_blocked)
    record_property("t29_leaks", leaks)

    assert foreign_inserts_blocked == len(range(1, TRANSACTION_COUNT, 5))
    assert len(rolled_back) == len(range(3, TRANSACTION_COUNT, 7))
    # Proof that the run went through a transaction pool: server connections were reused
    # across tenants. A direct connection per transaction would give 1,000 backends.
    assert len(backend_tenants) < TRANSACTION_COUNT // 10, (
        f"{len(backend_tenants)} server backends for {TRANSACTION_COUNT} transactions;"
        " T-29 must run through PgBouncer"
    )
    assert shared_backends > 0, "no server backend served more than one tenant"
    assert leaks == 0, f"detected {leaks} isolation leaks in {TRANSACTION_COUNT} transactions"
