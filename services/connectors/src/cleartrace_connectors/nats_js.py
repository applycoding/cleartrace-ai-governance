from __future__ import annotations

import contextlib
import json
import os
from uuid import UUID

import nats
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import RetentionPolicy, StorageType, StreamConfig

from cleartrace_connectors.postgres_outbox import PostgresOutbox

STREAM_NAME = "CLEARTRACE_OUTBOX"
CONSUMER_NAME = "cleartrace-outbox-consumer"


async def ensure_stream(nats_url: str) -> None:
    nc = await nats.connect(nats_url)
    js = nc.jetstream()
    config = StreamConfig(
        name=STREAM_NAME,
        subjects=["cleartrace.outbox.>"],
        retention=RetentionPolicy.LIMITS,
        storage=StorageType.MEMORY,
    )
    with contextlib.suppress(Exception):
        await js.add_stream(config=config)
    await nc.drain()


async def publish_outbox_batch(
    *,
    dsn: str,
    tenant_id: UUID,
    nats_url: str,
    limit: int = 200,
) -> int:
    outbox = PostgresOutbox(dsn, tenant_id)
    rows = outbox.fetch_unpublished(limit=limit)
    if not rows:
        return 0
    nc = await nats.connect(nats_url)
    js = nc.jetstream()
    published = 0
    for row in rows:
        subject = str(row["subject"]).replace(
            "cleartrace.connector.", "cleartrace.outbox.connector.", 1
        )
        body = json.dumps(row["payload"]).encode("utf-8")
        message_id = str(row["message_id"])
        await js.publish(subject, body, headers={"Nats-Msg-Id": message_id})
        outbox.mark_published(row["id"])
        published += 1
    await nc.drain()
    return published


async def consume_outbox_messages(
    *,
    dsn: str,
    nats_url: str,
    max_messages: int = 500,
    timeout_seconds: float = 1.0,
) -> int:
    nc = await nats.connect(nats_url)
    js = nc.jetstream()
    with contextlib.suppress(Exception):
        await js.add_consumer(
            STREAM_NAME,
            durable_name=CONSUMER_NAME,
            filter_subject="cleartrace.outbox.>",
        )
    sub = await js.pull_subscribe(
        "cleartrace.outbox.>",
        durable=CONSUMER_NAME,
    )
    processed = 0
    while processed < max_messages:
        try:
            msgs = await sub.fetch(batch=10, timeout=timeout_seconds)
        except NatsTimeoutError:
            break
        if not msgs:
            break
        for msg in msgs:
            msg_id: str | None = None
            if msg.headers:
                msg_id = msg.headers.get("Nats-Msg-Id")
            if msg_id is None:
                msg_id = str(msg.metadata.sequence.stream)
            if _mark_processed(dsn, str(msg_id)):
                processed += 1
            await msg.ack()
    await nc.drain()
    return processed


def _mark_processed(dsn: str, message_id: str) -> bool:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SET ROLE cleartrace_app")
        cur.execute(
            """
            INSERT INTO processed_event_ids (message_id)
            VALUES (%s)
            ON CONFLICT (message_id) DO NOTHING
            RETURNING message_id
            """,
            (message_id,),
        )
        return cur.fetchone() is not None


def default_nats_url() -> str:
    return os.environ.get("CLEARTRACE_NATS_URL", "nats://127.0.0.1:4222")
