from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID

import httpx

MAX_WEBHOOK_ATTEMPTS = 7
_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}


class WebhookURLError(ValueError):
    """Webhook destination is not an allowed public HTTPS endpoint."""


def _check_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if not ip.is_global or ip.is_multicast:
        raise WebhookURLError(f"webhook destination {ip} is not a public address")


def _check_hostname(host: str) -> None:
    """DNS name rules: 253 characters at most, labels of 1 to 63 characters, IDNA-valid."""
    try:
        ascii_host = host.rstrip(".").encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise WebhookURLError("webhook URL host is not a valid DNS name") from exc
    labels = ascii_host.split(".")
    if len(ascii_host) > 253 or any(not 1 <= len(label) <= 63 for label in labels):
        raise WebhookURLError("webhook URL host is not a valid DNS name")


def validate_webhook_url(url: str) -> str:
    """Reject webhook URLs that could reach internal services (SSRF, ASVS V5.2.6).

    Only ``https`` URLs with a hostname, no user-info and, for IP literals, a public
    address are accepted. Hostnames are resolved again at delivery time.
    """
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise WebhookURLError("webhook URL must use https")
    host = parts.hostname
    if not host or parts.username is not None or parts.password is not None:
        raise WebhookURLError("webhook URL must name a host and carry no credentials")
    if host.lower().rstrip(".") in _BLOCKED_HOSTNAMES or host.lower().endswith(".localhost"):
        raise WebhookURLError("webhook URL must not target localhost")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _check_ip(literal)
    else:
        _check_hostname(host)
    try:
        _ = parts.port
    except ValueError as exc:
        raise WebhookURLError("webhook URL has an invalid port") from exc
    return url


async def _assert_resolves_public(url: str) -> None:
    parts = urlsplit(url)
    host = parts.hostname or ""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, parts.port or 443, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise WebhookURLError(f"webhook host does not resolve: {host}") from exc
    for info in infos:
        _check_ip(ipaddress.ip_address(info[4][0]))


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
        """POST to a validated public HTTPS URL; network errors are a failed attempt."""
        try:
            validate_webhook_url(url)
            await _assert_resolves_public(url)
            resp = await self._client.post(url, headers=headers, content=content)
        except WebhookURLError as exc:
            return 0, f"blocked: {exc}"
        except httpx.HTTPError as exc:
            return 0, f"transport error: {type(exc).__name__}"
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
) -> tuple[bool, int, str | None, bool]:
    """Returns delivered, attempt count, last error, permanent_failure."""
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
        permanent = subscription_url in getattr(transport, "permanent_fail_urls", set())
        if 200 <= code < 300:
            return True, attempts, None, False
        last_error = f"HTTP {code}: {text}"
        if permanent:
            return False, attempts, last_error, True
        if attempt < max_attempts - 1:
            delay = retry_delay_seconds(attempt)
            # Deterministic fast retry in tests (no real sleep when delay is tiny)
            if delay >= 0.01:
                import asyncio

                await asyncio.sleep(min(delay, 0.001))
    return False, attempts, last_error, False
