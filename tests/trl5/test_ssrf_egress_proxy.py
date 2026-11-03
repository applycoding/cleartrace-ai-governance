from __future__ import annotations

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
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0177.0.0.1/",
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


@pytest.mark.asyncio
async def test_ssrf_refuses_redirect_response() -> None:
    client = _client(("httpbin.org", 443))
    # httpbin may be unreachable in CI; validate redirect refusal via pin on allowed host only.
    # Use mock: if we got 302, client raises — covered by unit patch below.
    from unittest.mock import AsyncMock, patch

    client = _client(("redirect.test", 443))
    pinned = PinnedConnection(host="redirect.test", port=443, pinned_ip="203.0.113.10")
    with patch.object(client, "pin", return_value=pinned):
        with patch(
            "httpx.AsyncClient.request",
            new=AsyncMock(return_value=type("R", (), {"status_code": 302})()),
        ):
            with pytest.raises(EgressDeniedError):
                await client.request("GET", "https://redirect.test/redirect")
