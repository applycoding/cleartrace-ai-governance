from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from uuid6 import uuid7

from cleartrace_notifier.models import (
    AlertPayload,
    AlertType,
    DeadLetterEntry,
    NotificationRecord,
    TicketLink,
    WebhookSubscription,
)
from cleartrace_notifier.store import NotificationStore


class PostgresNotificationStore(NotificationStore):
    """Tenant-scoped persistence through Postgres RLS."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    def save_subscription(self, sub: WebhookSubscription) -> None:
        with tenant_transaction(self._dsn, sub.tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO webhook_subscription (id, tenant_id, url, secret, channel, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (sub.id, sub.tenant_id, sub.url, sub.secret, sub.channel, sub.active),
            )

    def list_subscriptions(self, tenant_id: UUID) -> list[WebhookSubscription]:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tenant_id, url, secret, channel, active
                FROM webhook_subscription
                WHERE tenant_id = %s AND active = true
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
        return [
            WebhookSubscription(
                id=row[0],
                tenant_id=row[1],
                url=row[2],
                secret=row[3],
                channel=row[4],
                active=row[5],
            )
            for row in rows
        ]

    def get_open_ticket(self, tenant_id: UUID, dedup_key: str) -> TicketLink | None:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tenant_id, notification_id, external_system,
                       external_id, dedup_key, status
                FROM ticket_link
                WHERE tenant_id = %s AND dedup_key = %s AND status = 'open'
                LIMIT 1
                """,
                (tenant_id, dedup_key),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return TicketLink(
            id=row[0],
            tenant_id=row[1],
            notification_id=row[2],
            external_system=row[3],
            external_id=row[4],
            dedup_key=row[5],
            status=row[6],
        )

    def create_ticket(self, ticket: TicketLink) -> None:
        with tenant_transaction(self._dsn, ticket.tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ticket_link (
                  id, tenant_id, notification_id, external_system, external_id, dedup_key, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ticket.id,
                    ticket.tenant_id,
                    ticket.notification_id,
                    ticket.external_system,
                    ticket.external_id,
                    ticket.dedup_key,
                    ticket.status,
                ),
            )

    def update_ticket(self, ticket_id: UUID, external_id: str) -> None:
        raise NotImplementedError("update_ticket not used in TRL 5 path")

    def save_notification(self, record: NotificationRecord) -> None:
        alert = record.alert
        with tenant_transaction(self._dsn, record.tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notification (
                  id, tenant_id, alert_type, system_id, control_id, reason,
                  title_en, title_fr, body_en, body_fr, dedup_key, status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    record.id,
                    record.tenant_id,
                    str(alert.alert_type),
                    alert.system_id,
                    alert.control_id,
                    alert.reason,
                    alert.title_en,
                    alert.title_fr,
                    alert.body_en,
                    alert.body_fr,
                    alert.dedup_key(),
                    record.status.value,
                ),
            )

    def mark_delivered(self, tenant_id: UUID, notification_id: UUID) -> None:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE notification
                SET status = 'delivered', delivered_at = now()
                WHERE id = %s AND tenant_id = %s
                """,
                (notification_id, tenant_id),
            )

    def add_dead_letter(self, entry: DeadLetterEntry) -> None:
        with tenant_transaction(self._dsn, entry.tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dead_letter_queue (
                  id, tenant_id, notification_id, subscription_id, reason, payload
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    entry.id,
                    entry.tenant_id,
                    entry.notification_id,
                    entry.subscription_id,
                    entry.reason,
                    json.dumps(entry.payload),
                ),
            )

    def dead_letters(self, tenant_id: UUID) -> list[DeadLetterEntry]:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tenant_id, notification_id, subscription_id, reason, payload
                FROM dead_letter_queue WHERE tenant_id = %s
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
        return [
            DeadLetterEntry(
                id=row[0],
                tenant_id=row[1],
                notification_id=row[2],
                subscription_id=row[3],
                reason=row[4],
                payload=row[5],
            )
            for row in rows
        ]

    def is_event_processed(self, tenant_id: UUID, event_id: str) -> bool:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM notifier_idempotency WHERE tenant_id = %s AND event_id = %s",
                (tenant_id, event_id),
            )
            return cur.fetchone() is not None

    def mark_event_processed(self, tenant_id: UUID, event_id: str) -> None:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notifier_idempotency (tenant_id, event_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
                """,
                (tenant_id, event_id),
            )

    def open_notifications(self) -> list[NotificationRecord]:
        raise NotImplementedError("use tenant-scoped queries in production")

    def record_webhook_delivery(
        self,
        tenant_id: UUID,
        notification_id: UUID,
        subscription_id: UUID,
        attempt: int,
        status: str,
        response_code: int | None,
        error_message: str | None,
    ) -> None:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO webhook_delivery (
                  id, tenant_id, notification_id, subscription_id,
                  attempt, status, response_code, error_message
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    uuid7(),
                    tenant_id,
                    notification_id,
                    subscription_id,
                    attempt,
                    status,
                    response_code,
                    error_message,
                ),
            )

    def count_notifications(self, tenant_id: UUID) -> int:
        return self._count(tenant_id, "SELECT count(*) FROM notification WHERE tenant_id = %s")

    def count_delivered(self, tenant_id: UUID) -> int:
        return self._count(
            tenant_id,
            "SELECT count(*) FROM notification WHERE tenant_id = %s AND status = 'delivered'",
        )

    def count_open_tickets(self, tenant_id: UUID) -> int:
        return self._count(
            tenant_id,
            "SELECT count(*) FROM ticket_link WHERE tenant_id = %s AND status = 'open'",
        )

    def count_dead_letters(self, tenant_id: UUID) -> int:
        return self._count(
            tenant_id,
            "SELECT count(*) FROM dead_letter_queue WHERE tenant_id = %s",
        )

    def _count(self, tenant_id: UUID, query: str) -> int:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(query, (tenant_id,))
            row = cur.fetchone()
            assert row is not None
            return int(row[0])


def alert_from_dict(data: dict[str, Any]) -> AlertPayload:
    return AlertPayload(
        tenant_id=UUID(str(data["tenant_id"])),
        alert_type=AlertType(str(data.get("alert_type", "non_conformity"))),
        system_id=UUID(str(data["system_id"])) if data.get("system_id") else None,
        control_id=data.get("control_id"),
        reason=str(data["reason"]),
        title_en=str(data["title_en"]),
        title_fr=str(data["title_fr"]),
        body_en=str(data.get("body_en", "")),
        body_fr=str(data.get("body_fr", "")),
        event_id=data.get("event_id"),
    )
