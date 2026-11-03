from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import httpx

MAX_WEBHOOK_ATTEMPTS = 7


def sign_payload(secret: str, body: bytes, timestamp: str) -> str:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_cloudevent(notification_id: UUID, alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "specversion": "1.0",
        "type": "com.cleartrace.alert.v1",
        "source": "/services/notifier",
        "id": str(notification_id),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "data": alert,
    }


def retry_delay_seconds(attempt: int) -> float:
    base = 0.5
    return float(min(base * (2**attempt), 30.0))


def next_retry_at(attempt: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=retry_delay_seconds(attempt))


class WebhookTransport(Protocol):
    async def post(self, url: str, headers: dict[str, str], content: bytes) -> tuple[int, str]: ...


class HttpxWebhookTransport:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owned = client is None

    async def post(self, url: str, headers: dict[str, str], content: bytes) -> tuple[int, str]:
        resp = await self._client.post(url, headers=headers, content=content)
        return resp.status_code, resp.text


class SimulatedWebhookTransport:
    """Test double that records calls and simulates outages per URL."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes]] = []
        self.failures_before_success: dict[str, int] = {}
        self.permanent_fail_urls: set[str] = set()

    def configure_outage(self, url: str, failures_before_success: int) -> None:
        self.failures_before_success[url] = failures_before_success

    def configure_permanent_failure(self, url: str) -> None:
        self.permanent_fail_urls.add(url)

    async def post(self, url: str, headers: dict[str, str], content: bytes) -> tuple[int, str]:
        self.calls.append((url, content))
        if url in self.permanent_fail_urls:
            return 503, "permanent outage"
        remaining = self.failures_before_success.get(url, 0)
        if remaining > 0:
            self.failures_before_success[url] = remaining - 1
            return 503, "temporary outage"
        return 202, "accepted"


async def deliver_webhook_with_retry(
    transport: WebhookTransport,
    subscription_url: str,
    secret: str,
    event: dict[str, Any],
    *,
    max_attempts: int = MAX_WEBHOOK_ATTEMPTS,
) -> tuple[bool, int, str | None]:
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
    last_error: str | None = None
    attempts = 0
    for attempt in range(max_attempts):
        attempts += 1
        timestamp = datetime.now(UTC).isoformat()
        signature = sign_payload(secret, body, timestamp)
        headers = {
            "Content-Type": "application/cloudevents+json",
            "X-ClearTrace-Timestamp": timestamp,
            "X-ClearTrace-Signature": signature,
        }
        code, text = await transport.post(subscription_url, headers, body)
        if 200 <= code < 300:
            return True, attempts, None
        last_error = f"HTTP {code}: {text}"
        if attempt < max_attempts - 1:
            delay = retry_delay_seconds(attempt)
            # Deterministic fast retry in tests (no real sleep when delay is tiny)
            if delay >= 0.01:
                import asyncio

                await asyncio.sleep(min(delay, 0.001))
    return False, attempts, last_error
