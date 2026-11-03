from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import nats
from nats.aio.client import Client as NATSClient
from nats.js.api import RetentionPolicy, StreamConfig

STREAM_NAME = "CLEARTRACE_ALERTS"
SUBJECT_PREFIX = "tenant"


def alert_subject(tenant_id: UUID) -> str:
    return f"{SUBJECT_PREFIX}.{tenant_id}.notifications.alert"


async def ensure_alert_stream(nc: NATSClient) -> Any:
    js = nc.jetstream()
    config = StreamConfig(
        name=STREAM_NAME,
        subjects=[f"{SUBJECT_PREFIX}.*.notifications.alert"],
        retention=RetentionPolicy.LIMITS,
    )
    try:
        await js.add_stream(config=config)
    except Exception:
        await js.update_stream(config)
    return js


async def publish_alert_event(js: Any, tenant_id: UUID, payload: dict[str, Any]) -> None:
    subject = alert_subject(tenant_id)
    await js.publish(subject, json.dumps(payload, separators=(",", ":")).encode())


async def run_alert_consumer(
    nc: NATSClient,
    handler: Any,
    *,
    durable: str = "cleartrace-notifier",
    batch: int = 50,
) -> int:
    js = nc.jetstream()
    sub = await js.pull_subscribe(
        f"{SUBJECT_PREFIX}.*.notifications.alert",
        durable=durable,
        stream=STREAM_NAME,
    )
    processed = 0
    while processed < batch:
        try:
            messages = await sub.fetch(min(10, batch - processed), timeout=2)
        except nats.errors.TimeoutError:
            break
        for msg in messages:
            data = json.loads(msg.data.decode())
            await handler(data)
            await msg.ack()
            processed += 1
    return processed


async def with_nats(url: str) -> NATSClient:
    return await nats.connect(url)
