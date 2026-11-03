from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

import pytest
from cleartrace_notifier.models import AlertPayload, AlertType
from cleartrace_notifier.service import AlertDispatcher, NotifierService
from cleartrace_notifier.store import InMemoryNotificationStore
from cleartrace_notifier.webhook import (
    SimulatedWebhookTransport,
    deliver_webhook_with_retry,
    sign_payload,
)
from uuid6 import uuid7

TENANT = UUID("11111111-1111-7111-8111-111111111101")


def test_hmac_signature_roundtrip() -> None:
    body = b'{"id":"1"}'
    ts = "2026-11-03T00:00:00+00:00"
    sig = sign_payload("secret", body, ts)
    expected = hmac.new(
        b"secret",
        ts.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    assert sig == f"sha256={expected}"


@pytest.mark.asyncio
async def test_webhook_retry_after_outage() -> None:
    transport = SimulatedWebhookTransport()
    url = "https://example.test/hook"
    transport.configure_outage(url, 2)
    ok, attempts, err, _permanent = await deliver_webhook_with_retry(
        transport,
        url,
        "secret",
        {"specversion": "1.0", "type": "test"},
        max_attempts=5,
    )
    assert ok is True
    assert attempts == 3
    assert err is None


@pytest.mark.asyncio
async def test_duplicate_ticket_suppression() -> None:
    store = InMemoryNotificationStore()
    transport = SimulatedWebhookTransport()
    dispatcher = AlertDispatcher(store, transport)
    alert = AlertPayload(
        tenant_id=TENANT,
        alert_type=AlertType.NON_CONFORMITY,
        system_id=uuid7(),
        control_id="DADM-1.1",
        reason="missing_evidence",
        title_en="Missing evidence",
        title_fr="Preuve manquante",
        body_en="",
        body_fr="",
    )
    first = await dispatcher.dispatch(alert)
    second = await dispatcher.dispatch(alert)
    assert first.ticket_created is True
    assert second.duplicate_suppressed is True
    assert first.ticket_id == second.ticket_id
    open_tickets = [t for t in store.tickets.values() if t.status == "open"]
    assert len(open_tickets) == 1


@pytest.mark.asyncio
async def test_notifier_protocol_dispatch() -> None:
    svc = NotifierService()
    await svc.dispatch_alert(
        TENANT,
        {
            "alert_type": "quarantine_item",
            "reason": "conflict",
            "title_en": "Quarantine",
            "title_fr": "Quarantaine",
        },
    )
    assert len(svc.store.open_notifications()) == 1
