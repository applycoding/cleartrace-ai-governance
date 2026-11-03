"""TRL 5 — T-22: alert delivery with webhook outages, duplicates and DLQ."""

from __future__ import annotations

from uuid import UUID

import pytest
from cleartrace_notifier.models import AlertPayload, AlertType, WebhookSubscription
from cleartrace_notifier.service import AlertDispatcher
from cleartrace_notifier.store import InMemoryNotificationStore
from cleartrace_notifier.webhook import SimulatedWebhookTransport
from uuid6 import uuid7

TENANT = UUID("11111111-1111-7111-8111-111111111101")


@pytest.mark.asyncio
async def test_t22_alert_delivery() -> None:
    store = InMemoryNotificationStore()
    transport = SimulatedWebhookTransport()
    dispatcher = AlertDispatcher(store, transport)

    outage_urls = [f"https://hooks.test/outage-{i}" for i in range(10)]
    permanent_url = "https://hooks.test/permanent-fail"
    healthy_url = "https://hooks.test/healthy"

    for url in outage_urls:
        store.save_subscription(
            WebhookSubscription(id=uuid7(), tenant_id=TENANT, url=url, secret="s")
        )
        transport.configure_outage(url, 2)
    store.save_subscription(
        WebhookSubscription(id=uuid7(), tenant_id=TENANT, url=permanent_url, secret="s")
    )
    transport.configure_permanent_failure(permanent_url)
    store.save_subscription(
        WebhookSubscription(id=uuid7(), tenant_id=TENANT, url=healthy_url, secret="s")
    )

    delivered = 0
    duplicate_keys: set[str] = set()
    systems = [uuid7() for _ in range(30)]

    for i in range(50):
        system_idx = i if i < 30 else i - 30
        alert = AlertPayload(
            tenant_id=TENANT,
            alert_type=AlertType.NON_CONFORMITY,
            system_id=systems[system_idx],
            control_id="DADM-1.1",
            reason="missing_evidence",
            title_en=f"Alert {i}",
            title_fr=f"Alerte {i}",
            body_en="",
            body_fr="",
        )
        key = alert.dedup_key()
        if key in duplicate_keys:
            pass
        duplicate_keys.add(key)
        result = await dispatcher.dispatch(alert)
        if result.delivered:
            delivered += 1

    open_tickets = [t for t in store.tickets.values() if t.status == "open"]
    dlq = store.dead_letters(TENANT)

    assert delivered == 50
    assert len(open_tickets) == 30
    assert len(dlq) >= 50
    assert transport.calls
