from __future__ import annotations

import os
import random
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


def test_t29_zero_cross_tenant_leaks_over_pooled_connections(dsn: str) -> None:
    """T-29: 0 leaks in 1,000 mixed transactions over PgBouncer (10,000 deferred)."""
    leaks = 0
    rng = random.Random(29)
    for step in range(TRANSACTION_COUNT):
        tenant_id = TENANTS[step % len(TENANTS)]
        expected_marker = {TENANT_A: "MARKER-A", TENANT_B: "MARKER-B", TENANT_C: "MARKER-C"}[
            tenant_id
        ]
        with psycopg.connect(dsn, autocommit=False, prepare_threshold=None) as raw_conn, raw_conn.cursor() as cur:
            cur.execute("SELECT current_setting('app.tenant_id', true)")
            stale = cur.fetchone()
            if stale and stale[0]:
                leaks += 1
        with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
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
            probe = uuid7()
            cur.execute(
                "INSERT INTO ai_system (id, tenant_id, system_key) VALUES (%s, %s, %s)",
                (probe, tenant_id, f"TMP-{step}-{rng.randint(0, 9999)}"),
            )
            cur.execute(
                "SELECT count(*) FROM ai_system WHERE tenant_id <> %s",
                (tenant_id,),
            )
            foreign = cur.fetchone()
            if foreign and int(foreign[0]) > 0:
                leaks += 1
    assert leaks == 0, f"detected {leaks} isolation leaks in {TRANSACTION_COUNT} transactions"
