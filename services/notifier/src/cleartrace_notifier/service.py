from __future__ import annotations

from typing import Any
from uuid import UUID

from uuid6 import uuid7

from cleartrace_notifier.digest import DigestDocument, build_digest
from cleartrace_notifier.models import (
    AlertPayload,
    DeadLetterEntry,
    DispatchResult,
    NotificationRecord,
)
from cleartrace_notifier.store import (
    InMemoryNotificationStore,
    NotificationStore,
    new_notification,
    new_ticket,
)
from cleartrace_notifier.webhook import (
    HttpxWebhookTransport,
    SimulatedWebhookTransport,
    WebhookTransport,
    build_cloudevent,
    deliver_webhook_with_retry,
)


class AlertDispatcher:
    """Delivers alerts with deduplicated tickets and signed webhook retries."""

    def __init__(
        self,
        store: NotificationStore,
        transport: WebhookTransport | None = None,
    ) -> None:
        self._store = store
        self._transport = transport or HttpxWebhookTransport()

    async def dispatch(self, alert: AlertPayload) -> DispatchResult:
        if alert.event_id and self._store.is_event_processed(alert.tenant_id, alert.event_id):
            existing = self._find_by_event(alert.tenant_id, alert.event_id)
            nid = existing.id if existing else uuid7()
            return DispatchResult(
                notification_id=nid,
                delivered=True,
                ticket_created=False,
                ticket_id=None,
                webhook_attempts=0,
                duplicate_suppressed=True,
            )

        dedup_key = alert.dedup_key()
        open_ticket = self._store.get_open_ticket(alert.tenant_id, dedup_key)
        ticket_created = False
        ticket_id: str | None = None
        duplicate_suppressed = open_ticket is not None

        record = new_notification(alert)
        self._store.save_notification(record)

        if open_ticket is None:
            ticket = new_ticket(alert.tenant_id, record.id, dedup_key)
            self._store.create_ticket(ticket)
            ticket_created = True
            ticket_id = ticket.external_id
        else:
            ticket_id = open_ticket.external_id

        event = build_cloudevent(
            record.id,
            {
                "alert_type": str(alert.alert_type),
                "system_id": str(alert.system_id) if alert.system_id else None,
                "control_id": alert.control_id,
                "reason": alert.reason,
                "title_en": alert.title_en,
                "title_fr": alert.title_fr,
                "ticket_id": ticket_id,
            },
        )

        subs = self._store.list_subscriptions(alert.tenant_id)
        total_attempts = 0
        any_webhook_ok = not subs
        for sub in subs:
            ok, attempts, err = await deliver_webhook_with_retry(
                self._transport,
                sub.url,
                sub.secret,
                event,
            )
            total_attempts += attempts
            if ok:
                any_webhook_ok = True
            else:
                self._store.add_dead_letter(
                    DeadLetterEntry(
                        id=uuid7(),
                        tenant_id=alert.tenant_id,
                        notification_id=record.id,
                        subscription_id=sub.id,
                        reason=err or "delivery failed",
                        payload=event,
                    )
                )

        # In-app delivery always succeeds; webhooks may land in the DLQ.
        delivered = True
        self._store.mark_delivered(record.id)
        _ = any_webhook_ok or not subs
        if alert.event_id:
            self._store.mark_event_processed(alert.tenant_id, alert.event_id)

        return DispatchResult(
            notification_id=record.id,
            delivered=delivered,
            ticket_created=ticket_created,
            ticket_id=ticket_id,
            webhook_attempts=total_attempts,
            duplicate_suppressed=duplicate_suppressed,
        )

    def _find_by_event(self, tenant_id: UUID, event_id: str) -> NotificationRecord | None:
        for record in self._store.open_notifications():
            if record.tenant_id == tenant_id and record.alert.event_id == event_id:
                return record
        return None


class NotifierService:
    """Implements the cleartrace_contracts Notifier protocol."""

    def __init__(self, store: NotificationStore | None = None) -> None:
        self._store = store or InMemoryNotificationStore()
        self._dispatcher = AlertDispatcher(self._store)

    @property
    def store(self) -> NotificationStore:
        return self._store

    async def dispatch_alert(self, tenant_id: UUID, alert: dict[str, object]) -> None:
        payload = AlertPayload(
            tenant_id=tenant_id,
            alert_type=str(alert.get("alert_type", "non_conformity")),
            system_id=_coerce_uuid(alert.get("system_id")),
            control_id=_optional_str(alert.get("control_id")),
            reason=str(alert.get("reason", "unspecified")),
            title_en=str(alert.get("title_en", "Alert")),
            title_fr=str(alert.get("title_fr", "Alerte")),
            body_en=str(alert.get("body_en", "")),
            body_fr=str(alert.get("body_fr", "")),
            event_id=_optional_str(alert.get("event_id")),
            metadata=_coerce_dict(alert.get("metadata")),
        )
        await self._dispatcher.dispatch(payload)

    async def build_digest(
        self,
        tenant_id: UUID,
        *,
        language: str = "en",
    ) -> DigestDocument:
        notes = [
            n
            for n in self._store.open_notifications()
            if n.tenant_id == tenant_id and n.delivered_at is not None
        ]
        lang: Any = "fr" if language.startswith("fr") else "en"
        return build_digest(tenant_id, notes, language=lang)


def _coerce_uuid(value: object | None) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _coerce_dict(value: object | None) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


__all__ = ["AlertDispatcher", "NotifierService", "SimulatedWebhookTransport"]
