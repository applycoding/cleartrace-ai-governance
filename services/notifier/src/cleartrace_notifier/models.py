from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class AlertType(StrEnum):
    NON_CONFORMITY = "non_conformity"
    REASSESSMENT_REQUIRED = "reassessment_required"
    EVIDENCE_EXPIRING = "evidence_expiring"
    APPROVAL_EXPIRING = "approval_expiring"
    BINDING_BREACH = "binding_breach"
    QUARANTINE_ITEM = "quarantine_item"
    JIT_GRANT_USED = "jit_grant_used"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DLQ = "dlq"


@dataclass(slots=True)
class WebhookSubscription:
    id: UUID
    tenant_id: UUID
    url: str
    secret: str
    channel: str = "generic"
    active: bool = True


@dataclass(slots=True)
class AlertPayload:
    tenant_id: UUID
    alert_type: AlertType | str
    system_id: UUID | None
    control_id: str | None
    reason: str
    title_en: str
    title_fr: str
    body_en: str
    body_fr: str
    event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def dedup_key(self) -> str:
        system = str(self.system_id) if self.system_id else "none"
        control = self.control_id or "none"
        return f"{system}:{control}:{self.reason}"


@dataclass(slots=True)
class NotificationRecord:
    id: UUID
    tenant_id: UUID
    alert: AlertPayload
    status: DeliveryStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    delivered_at: datetime | None = None


@dataclass(slots=True)
class TicketLink:
    id: UUID
    tenant_id: UUID
    notification_id: UUID
    external_system: str
    external_id: str
    dedup_key: str
    status: str = "open"


@dataclass(slots=True)
class DeadLetterEntry:
    id: UUID
    tenant_id: UUID
    notification_id: UUID
    subscription_id: UUID
    reason: str
    payload: dict[str, Any]


@dataclass(slots=True)
class DispatchResult:
    notification_id: UUID
    delivered: bool
    ticket_created: bool
    ticket_id: str | None
    webhook_attempts: int
    duplicate_suppressed: bool
