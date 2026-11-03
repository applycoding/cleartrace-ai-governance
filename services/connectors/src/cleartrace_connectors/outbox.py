from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from uuid6 import uuid7


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    id: UUID
    tenant_id: UUID
    subject: str
    payload: dict[str, Any]
    message_id: str
    created_at: datetime


class InMemoryOutbox:
    def __init__(self) -> None:
        self.pending: deque[OutboxMessage] = deque()
        self.published: list[OutboxMessage] = []

    def enqueue(self, tenant_id: UUID, subject: str, payload: dict[str, Any]) -> OutboxMessage:
        msg = OutboxMessage(
            id=uuid7(),
            tenant_id=tenant_id,
            subject=subject,
            payload=payload,
            message_id=str(uuid7()),
            created_at=datetime.now(tz=UTC),
        )
        self.pending.append(msg)
        return msg

    def publish_batch(self, limit: int = 100) -> list[OutboxMessage]:
        batch: list[OutboxMessage] = []
        while self.pending and len(batch) < limit:
            batch.append(self.pending.popleft())
        self.published.extend(batch)
        return batch


class NatsJetStreamConsumer:
    """In-process NATS stand-in with deduplicated message ids."""

    def __init__(self) -> None:
        self.processed: set[str] = set()
        self.delivered: list[OutboxMessage] = []

    async def consume(self, messages: list[OutboxMessage]) -> int:
        count = 0
        for msg in messages:
            if msg.message_id in self.processed:
                continue
            await asyncio.sleep(0)
            self.processed.add(msg.message_id)
            self.delivered.append(msg)
            count += 1
        return count
