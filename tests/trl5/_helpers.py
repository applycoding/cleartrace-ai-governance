"""Test helpers for Package B TRL5 and integration tests."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from psycopg import connect
from uuid6 import uuid7

TENANT_ALPHA = UUID("11111111-1111-7111-8111-111111111101")


def pg_dsn() -> str:
    host = os.environ.get("CLEARTRACE_PGBOUNCER_HOST", "127.0.0.1")
    port = os.environ.get("CLEARTRACE_PGBOUNCER_PORT", "6432")
    return os.environ.get(
        "CLEARTRACE_TEST_DSN",
        f"postgresql://cleartrace_app:cleartrace_app@{host}:{port}/cleartrace",
    )


def migrator_dsn() -> str:
    return os.environ.get(
        "CLEARTRACE_MIGRATOR_DSN",
        "postgresql://cleartrace_super@127.0.0.1:5433/cleartrace",
    )


@contextmanager
def migrator_tenant_tx(tenant_id: UUID):
    with connect(migrator_dsn(), autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def ensure_principal(
    dsn: str,
    *,
    tenant_id: UUID,
    role_code: str,
    email_suffix: str,
) -> UUID:
    _ = dsn
    principal_id = uuid7()
    with migrator_tenant_tx(tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO principal (id, tenant_id, external_id, email, display_name)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                principal_id,
                tenant_id,
                f"ext-{email_suffix}",
                f"{email_suffix}@example.com",
                f"Test User {email_suffix}",
            ),
        )
        cur.execute(
            """
            INSERT INTO role_assignment (
              id, tenant_id, principal_id, role_code, valid_from, valid_to, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, NULL, now())
            """,
            (
                uuid7(),
                tenant_id,
                principal_id,
                role_code,
                datetime.now(tz=UTC) - timedelta(days=1),
            ),
        )
    return principal_id


def ensure_system_with_owner(
    dsn: str,
    *,
    tenant_id: UUID,
    owner_principal_id: UUID,
    system_key: str = "SYS-TEST",
) -> UUID:
    _ = dsn
    system_id = uuid7()
    with migrator_tenant_tx(tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_system (id, tenant_id, system_key)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (system_id, tenant_id, system_key),
        )
        cur.execute(
            """
            INSERT INTO ai_system_owner (tenant_id, ai_system_id, principal_id)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (tenant_id, system_id, owner_principal_id),
        )
    return system_id
