from __future__ import annotations

import socket
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from cleartrace_egress_proxy.client import EgressClient, PinnedConnection
from cleartrace_egress_proxy.profiles import (
    DestinationProfile,
    DestinationProfileSet,
    EgressDeniedError,
)


def _client(*hosts: tuple[str, int]) -> EgressClient:
    profiles = DestinationProfileSet(
        [DestinationProfile(host=host, port=port) for host, port in hosts]
    )
    return EgressClient(profiles)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/secret",
        "http://localhost/admin",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://metadata.goog/computeMetadata/v1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0177.0.0.1/",
        "http://010.000.000.001/",
        "http://evil.example.com:8080/",
        "ftp://allowed.example.com/data",
        "http://storage.googleapis.com/bucket",
    ],
)
def test_ssrf_blocked_destinations(url: str) -> None:
    client = _client(("allowed.example.com", 443))
    with pytest.raises(EgressDeniedError):
        client.pin(url)


def test_ssrf_allows_pinned_public_host() -> None:
    client = _client(("example.com", 443))
    pinned = client.pin("https://example.com/path")
    assert pinned.host == "example.com"
    assert pinned.port == 443
    assert pinned.pinned_ip


def test_ssrf_dns_rebinding_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(host: str, port: int, *_args: object, **_kwargs: object) -> list[tuple]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.5", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    client = _client(("rebind.test", 443))
    with pytest.raises(EgressDeniedError):
        client.pin("https://rebind.test/resource")


def test_ssrf_rejects_ipv6_metadata_mapped_loopback() -> None:
    client = _client(("allowed.example.com", 443))
    with pytest.raises(EgressDeniedError):
        client.pin("http://[::ffff:169.254.169.254]/")


@pytest.mark.asyncio
async def test_ssrf_refuses_redirect_response() -> None:
    client = _client(("redirect.test", 443))
    pinned = PinnedConnection(host="redirect.test", port=443, pinned_ip="203.0.113.10")
    with patch.object(client, "pin", return_value=pinned):
        with patch(
            "cleartrace_egress_proxy.transport.PinnedAsyncHTTPTransport.handle_async_request",
            new=AsyncMock(return_value=httpx.Response(302)),
        ):
            with pytest.raises(EgressDeniedError):
                await client.request("GET", "https://redirect.test/redirect")
