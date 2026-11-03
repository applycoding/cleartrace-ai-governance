from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from psycopg import Connection, sql


@contextmanager
def tenant_transaction(
    dsn: str,
    tenant_id: UUID,
    *,
    role: str = "cleartrace_app",
) -> Iterator[Connection[Any]]:
    """Open a transaction with tenant context for RLS (PgBouncer-safe SET LOCAL)."""
    with psycopg.connect(dsn, autocommit=False, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("could not read current_user")
            current = row[0]
            if current != role:
                cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
            cur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


class TenantConnection:
    """Helper for tests that reuse a single connection."""

    def __init__(self, dsn: str, tenant_id: UUID, role: str = "cleartrace_app") -> None:
        self._dsn = dsn
        self._tenant_id = tenant_id
        self._role = role

    @contextmanager
    def transaction(self) -> Iterator[Connection[Any]]:
        with tenant_transaction(self._dsn, self._tenant_id, role=self._role) as conn:
            yield conn
