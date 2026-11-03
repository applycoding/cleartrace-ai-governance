"""TRL 5 — T-22: alert delivery with webhook outages, duplicates and DLQ."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import time
from pathlib import Path
from uuid import UUID

import nats
import psycopg
import pytest
from cleartrace_notifier.models import AlertType, WebhookSubscription
from cleartrace_notifier.nats_bus import (
    STREAM_NAME,
    ensure_alert_stream,
    publish_alert_event,
    run_alert_consumer,
)
from cleartrace_notifier.postgres_store import PostgresNotificationStore, alert_from_dict
from cleartrace_notifier.service import AlertDispatcher
from cleartrace_notifier.webhook import SimulatedWebhookTransport
from uuid6 import uuid7

from tests.trl5._helpers import migrator_dsn, pg_dsn

TENANT = UUID("11111111-1111-7111-8111-111111111101")
OUTAGE_WEBHOOK_COUNT = 10
ALERT_COUNT = 50
UNIQUE_ALERT_COUNT = 30
DUPLICATE_ALERT_COUNT = 20
EXPECTED_DLQ = 50
EXPECTED_TICKETS = 30


def _reset_notifier_data() -> None:
    super_dsn = migrator_dsn()
    with psycopg.connect(super_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            TRUNCATE dead_letter_queue, webhook_delivery, ticket_link, notification,
              webhook_subscription, notifier_idempotency RESTART IDENTITY CASCADE
            """
        )


@pytest.fixture(scope="module")
def nats_server() -> str:
    url = os.environ.get("CLEARTRACE_NATS_URL", "nats://127.0.0.1:4222")

    if os.environ.get("CLEARTRACE_CI") == "1":
        for _ in range(60):
            try:
                asyncio.run(_ping(url))
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("NATS not reachable; ensure ci_compose_stack started nats service")
        yield url
        return

    if shutil.which("nats-server") is None:
        bin_dir = Path(__file__).resolve().parents[2] / ".data" / "nats"
        bin_dir.mkdir(parents=True, exist_ok=True)
        if not (bin_dir / "nats-server").exists():
            subprocess.run(
                [
                    "curl",
                    "-fsSL",
                    "https://github.com/nats-io/nats-server/releases/download/v2.10.24/nats-server-v2.10.24-linux-amd64.tar.gz",
                    "-o",
                    str(bin_dir / "nats.tgz"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "tar",
                    "-xzf",
                    str(bin_dir / "nats.tgz"),
                    "-C",
                    str(bin_dir),
                    "--strip-components=1",
                ],
                check=True,
            )
        nats_bin = bin_dir / "nats-server"
    else:
        nats_bin = Path(shutil.which("nats-server") or "nats-server")

    log = Path(__file__).resolve().parents[2] / ".data" / "nats.log"
    proc = subprocess.Popen(
        [str(nats_bin), "-js", "-p", "4222"],
        stdout=log.open("w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(30):
        try:
            asyncio.run(_ping(url))
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError("nats-server failed to start")
    yield url
    proc.terminate()
    proc.wait(timeout=5)


async def _ping(url: str) -> None:
    nc = await nats.connect(url)
    await nc.close()


@pytest.fixture(scope="module")
def notifier_dsn() -> str:
    return os.environ.get("CLEARTRACE_NOTIFIER_DSN") or pg_dsn()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_t22_alert_delivery(nats_server: str, notifier_dsn: str) -> None:
    _reset_notifier_data()
    store = PostgresNotificationStore(notifier_dsn)
    transport = SimulatedWebhookTransport()
    dispatcher = AlertDispatcher(store, transport)

    outage_urls = [f"https://hooks.test/outage-{i}" for i in range(OUTAGE_WEBHOOK_COUNT)]
    permanent_url = "https://hooks.test/permanent-fail"
    for url in outage_urls:
        store.save_subscription(
            WebhookSubscription(id=uuid7(), tenant_id=TENANT, url=url, secret="s")
        )
        transport.configure_outage(url, 2)
    permanent_sub = WebhookSubscription(
        id=uuid7(), tenant_id=TENANT, url=permanent_url, secret="s"
    )
    store.save_subscription(permanent_sub)
    transport.configure_permanent_failure(permanent_url)

    systems = [uuid7() for _ in range(UNIQUE_ALERT_COUNT)]
    payloads: list[dict[str, object]] = []
    for i in range(ALERT_COUNT):
        system_idx = i if i < UNIQUE_ALERT_COUNT else i - UNIQUE_ALERT_COUNT
        payloads.append(
            {
                "tenant_id": str(TENANT),
                "alert_type": AlertType.NON_CONFORMITY.value,
                "system_id": str(systems[system_idx]),
                "control_id": "DADM-1.1",
                "reason": "missing_evidence",
                "title_en": f"Alert {i}",
                "title_fr": f"Alerte {i}",
                "body_en": "",
                "body_fr": "",
            }
        )

    nc = await nats.connect(nats_server)
    js = await ensure_alert_stream(nc)
    with contextlib.suppress(Exception):
        await js.purge_stream(STREAM_NAME)

    async def handle(data: dict[str, object]) -> None:
        alert = alert_from_dict(data)
        await dispatcher.dispatch(alert)

    for payload in payloads:
        await publish_alert_event(js, TENANT, payload)

    processed = await run_alert_consumer(nc, handle, batch=ALERT_COUNT)
    await nc.close()

    assert processed == ALERT_COUNT
    assert store.count_delivered(TENANT) == ALERT_COUNT
    assert store.count_open_tickets(TENANT) == EXPECTED_TICKETS
    assert store.count_dead_letters(TENANT) == EXPECTED_DLQ
    assert store.count_notifications(TENANT) == ALERT_COUNT

    duplicate_ticket_attempts = ALERT_COUNT - EXPECTED_TICKETS
    assert duplicate_ticket_attempts == DUPLICATE_ALERT_COUNT
