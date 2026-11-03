from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from psycopg.types.json import Jsonb
from uuid6 import uuid7


class PostgresOutbox:
    def __init__(self, dsn: str, tenant_id: UUID) -> None:
        self._dsn = dsn
        self._tenant_id = tenant_id

    def enqueue(self, subject: str, payload: dict[str, Any]) -> str:
        message_id = str(uuid7())
        row_id = uuid7()
        with tenant_transaction(self._dsn, self._tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outbox (id, tenant_id, subject, payload, message_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (row_id, self._tenant_id, subject, Jsonb(payload), message_id),
            )
        return message_id

    def fetch_unpublished(self, limit: int = 100) -> list[dict[str, Any]]:
        with tenant_transaction(self._dsn, self._tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, subject, payload, message_id
                FROM outbox
                WHERE tenant_id = %s AND published_at IS NULL
                ORDER BY created_at
                LIMIT %s
                """,
                (self._tenant_id, limit),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "subject": row[1],
                "payload": row[2],
                "message_id": row[3],
            }
            for row in rows
        ]

    def mark_published(self, outbox_id: UUID) -> None:
        with tenant_transaction(self._dsn, self._tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE outbox SET published_at = %s WHERE id = %s AND tenant_id = %s",
                (datetime.now(tz=UTC), outbox_id, self._tenant_id),
            )
