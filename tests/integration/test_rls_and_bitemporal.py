from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from cleartrace_db.session import tenant_transaction
from uuid6 import uuid7

TENANT_A = UUID("11111111-1111-7111-8111-111111111101")
TENANT_B = UUID("11111111-1111-7111-8111-111111111102")


def _pgbouncer_dsn() -> str:
    host = os.environ.get("CLEARTRACE_PGBOUNCER_HOST", "127.0.0.1")
    port = os.environ.get("CLEARTRACE_PGBOUNCER_PORT", "6432")
    return f"postgresql://cleartrace_app:cleartrace_app@{host}:{port}/cleartrace"


@pytest.fixture(scope="module")
def dsn() -> str:
    return os.environ.get("CLEARTRACE_TEST_DSN") or _pgbouncer_dsn()


@pytest.fixture(scope="module", autouse=True)
def seed_systems(dsn: str) -> None:
    for tenant_id, key in ((TENANT_A, "SYS-A"), (TENANT_B, "SYS-B")):
        system_id = uuid7()
        with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    INSERT INTO ai_system (id, tenant_id, system_key)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                (system_id, tenant_id, key),
            )


def test_rls_no_cross_tenant_leaks(dsn: str) -> None:
    leaks = 0
    for _ in range(50):
        with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
            cur.execute("SELECT system_key, tenant_id FROM ai_system")
            rows = cur.fetchall()
            for _key, tid in rows:
                if tid != TENANT_A:
                    leaks += 1
        with tenant_transaction(dsn, TENANT_B) as conn, conn.cursor() as cur:
            cur.execute("SELECT system_key, tenant_id FROM ai_system")
            rows = cur.fetchall()
            for _key, tid in rows:
                if tid != TENANT_B:
                    leaks += 1
    assert leaks == 0


def test_bitemporal_as_of_query(dsn: str) -> None:
    system_id = uuid7()
    version_old = uuid7()
    version_new = uuid7()
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2025, 1, 1, tzinfo=UTC)

    system_key = f"SYS-BITEMP-{uuid7()}"
    with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ai_system (id, tenant_id, system_key) VALUES (%s, %s, %s)",
            (system_id, TENANT_A, system_key),
        )
        cur.execute(
            """
                SELECT cleartrace_close_and_insert_system_version(
                  %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
            (
                TENANT_A,
                system_id,
                "Name EN v1",
                "Nom FR v1",
                "Desc EN v1",
                "Desc FR v1",
                t0,
                version_old,
            ),
        )
        cur.execute(
            """
                SELECT cleartrace_close_and_insert_system_version(
                  %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
            (
                TENANT_A,
                system_id,
                "Name EN v2",
                "Nom FR v2",
                "Desc EN v2",
                "Desc FR v2",
                t1,
                version_new,
            ),
        )

    as_of = t0 + timedelta(hours=1)
    with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT name_en FROM ai_system_version
                WHERE ai_system_id = %s
                  AND valid_from <= %s
                  AND (valid_to IS NULL OR valid_to > %s)
                ORDER BY valid_from DESC
                LIMIT 1
                """,
            (system_id, as_of, as_of),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "Name EN v1"

    as_of2 = t1 + timedelta(hours=1)
    with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT name_en FROM ai_system_version
                WHERE ai_system_id = %s
                  AND valid_from <= %s
                  AND (valid_to IS NULL OR valid_to > %s)
                ORDER BY valid_from DESC
                LIMIT 1
                """,
            (system_id, as_of2, as_of2),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "Name EN v2"
