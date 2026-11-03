from __future__ import annotations

import os
from uuid import UUID

import psycopg
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


@pytest.mark.integration
def test_risk_tables_rls_isolation(dsn: str) -> None:
    metric_a = uuid7()
    metric_b = uuid7()
    system_a = uuid7()
    system_b = uuid7()
    version_a = uuid7()
    version_b = uuid7()
    obs_a = uuid7()
    obs_b = uuid7()

    with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_system (id, tenant_id, system_key)
            VALUES (%s, %s, 'RISK-A')
            """,
            (system_a, TENANT_A),
        )
        cur.execute(
            """
            INSERT INTO metric_definition (
              id, tenant_id, code, area, name_en, name_fr, library
            ) VALUES (%s, %s, 'test.metric.a', 'data', 'A', 'A', 'cleartrace')
            """,
            (metric_a, TENANT_A),
        )
        cur.execute(
            """
            INSERT INTO metric_version (
              id, tenant_id, metric_definition_id, version_number,
              unit, window_kind, aggregation
            ) VALUES (%s, %s, %s, 1, 'ratio', 'rolling', 'mean')
            """,
            (version_a, TENANT_A, metric_a),
        )
        cur.execute(
            """
            INSERT INTO metric_observation (
              id, tenant_id, ai_system_id, metric_version_id,
              window_start, window_end, value, status
            ) VALUES (%s, %s, %s, %s, now(), now(), 0.1, 'ok')
            """,
            (obs_a, TENANT_A, system_a, version_a),
        )

    with tenant_transaction(dsn, TENANT_B) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_system (id, tenant_id, system_key)
            VALUES (%s, %s, 'RISK-B')
            """,
            (system_b, TENANT_B),
        )
        cur.execute(
            """
            INSERT INTO metric_definition (
              id, tenant_id, code, area, name_en, name_fr, library
            ) VALUES (%s, %s, 'test.metric.b', 'data', 'B', 'B', 'cleartrace')
            """,
            (metric_b, TENANT_B),
        )
        cur.execute(
            """
            INSERT INTO metric_version (
              id, tenant_id, metric_definition_id, version_number,
              unit, window_kind, aggregation
            ) VALUES (%s, %s, %s, 1, 'ratio', 'rolling', 'mean')
            """,
            (version_b, TENANT_B, metric_b),
        )
        cur.execute(
            """
            INSERT INTO metric_observation (
              id, tenant_id, ai_system_id, metric_version_id,
              window_start, window_end, value, status
            ) VALUES (%s, %s, %s, %s, now(), now(), 0.2, 'ok')
            """,
            (obs_b, TENANT_B, system_b, version_b),
        )

    leaks = 0
    with tenant_transaction(dsn, TENANT_A) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, tenant_id FROM metric_observation")
        for obs_id, tenant_id in cur.fetchall():
            if tenant_id != TENANT_A or obs_id == obs_b:
                leaks += 1
    with tenant_transaction(dsn, TENANT_B) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, tenant_id FROM metric_observation")
        for obs_id, tenant_id in cur.fetchall():
            if tenant_id != TENANT_B or obs_id == obs_a:
                leaks += 1
    assert leaks == 0


@pytest.mark.integration
@pytest.mark.parametrize("table", ["metric_observation", "risk_item_version"])
@pytest.mark.parametrize("statement", ["UPDATE {t} SET tenant_id = tenant_id", "DELETE FROM {t}"])
def test_risk_append_only_tables_reject_update_and_delete(
    dsn: str, table: str, statement: str
) -> None:
    with (
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        tenant_transaction(dsn, TENANT_A) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(statement.format(t=table))  # table names come from the fixed list above
