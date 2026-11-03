from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from uuid6 import uuid7

from cleartrace_notifier.models import (
    AlertPayload,
    DeadLetterEntry,
    DeliveryStatus,
    NotificationRecord,
    TicketLink,
    WebhookSubscription,
)


class NotificationStore(Protocol):
    def save_subscription(self, sub: WebhookSubscription) -> None: ...

    def list_subscriptions(self, tenant_id: UUID) -> list[WebhookSubscription]: ...

    def get_open_ticket(self, tenant_id: UUID, dedup_key: str) -> TicketLink | None: ...

    def create_ticket(self, ticket: TicketLink) -> None: ...

    def update_ticket(self, ticket_id: UUID, external_id: str) -> None: ...

    def save_notification(self, record: NotificationRecord) -> None: ...

    def mark_delivered(self, notification_id: UUID) -> None: ...

    def add_dead_letter(self, entry: DeadLetterEntry) -> None: ...

    def dead_letters(self, tenant_id: UUID) -> list[DeadLetterEntry]: ...

    def is_event_processed(self, tenant_id: UUID, event_id: str) -> bool: ...

    def mark_event_processed(self, tenant_id: UUID, event_id: str) -> None: ...

    def open_notifications(self) -> list[NotificationRecord]: ...


@dataclass
class InMemoryNotificationStore:
    subscriptions: list[WebhookSubscription] = field(default_factory=list)
    notifications: dict[UUID, NotificationRecord] = field(default_factory=dict)
    tickets: dict[UUID, TicketLink] = field(default_factory=dict)
    dlq_entries: list[DeadLetterEntry] = field(default_factory=list)
    processed_events: set[tuple[UUID, str]] = field(default_factory=set)

    def save_subscription(self, sub: WebhookSubscription) -> None:
        self.subscriptions.append(sub)

    def list_subscriptions(self, tenant_id: UUID) -> list[WebhookSubscription]:
        return [s for s in self.subscriptions if s.tenant_id == tenant_id and s.active]

    def get_open_ticket(self, tenant_id: UUID, dedup_key: str) -> TicketLink | None:
        for ticket in self.tickets.values():
            if (
                ticket.tenant_id == tenant_id
                and ticket.dedup_key == dedup_key
                and ticket.status == "open"
            ):
                return ticket
        return None

    def create_ticket(self, ticket: TicketLink) -> None:
        self.tickets[ticket.id] = ticket

    def update_ticket(self, ticket_id: UUID, external_id: str) -> None:
        ticket = self.tickets[ticket_id]
        ticket.external_id = external_id

    def save_notification(self, record: NotificationRecord) -> None:
        self.notifications[record.id] = record

    def mark_delivered(self, notification_id: UUID) -> None:
        record = self.notifications[notification_id]
        record.status = DeliveryStatus.DELIVERED
        record.delivered_at = datetime.now(UTC)

    def add_dead_letter(self, entry: DeadLetterEntry) -> None:
        self.dlq_entries.append(entry)

    def dead_letters(self, tenant_id: UUID) -> list[DeadLetterEntry]:
        return [d for d in self.dlq_entries if d.tenant_id == tenant_id]

    def is_event_processed(self, tenant_id: UUID, event_id: str) -> bool:
        return (tenant_id, event_id) in self.processed_events

    def mark_event_processed(self, tenant_id: UUID, event_id: str) -> None:
        self.processed_events.add((tenant_id, event_id))

    def open_notifications(self) -> list[NotificationRecord]:
        return list(self.notifications.values())


def new_ticket(
    tenant_id: UUID,
    notification_id: UUID,
    dedup_key: str,
    external_system: str = "simulator",
) -> TicketLink:
    return TicketLink(
        id=uuid7(),
        tenant_id=tenant_id,
        notification_id=notification_id,
        external_system=external_system,
        external_id=f"TCK-{uuid7()}",
        dedup_key=dedup_key,
    )


def new_notification(alert: AlertPayload) -> NotificationRecord:
    return NotificationRecord(
        id=uuid7(),
        tenant_id=alert.tenant_id,
        alert=alert,
        status=DeliveryStatus.PENDING,
    )
