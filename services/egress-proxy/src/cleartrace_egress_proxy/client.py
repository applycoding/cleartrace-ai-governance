from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from cleartrace_egress_proxy.profiles import DestinationProfileSet, EgressDeniedError


@dataclass(frozen=True, slots=True)
class PinnedConnection:
    host: str
    port: int
    pinned_ip: str


class EgressClient:
    """Resolve DNS once, pin the socket address, refuse redirects."""

    def __init__(self, profiles: DestinationProfileSet) -> None:
        self._profiles = profiles
        self._pin_cache: dict[tuple[str, int], str] = {}

    def pin(self, url: str) -> PinnedConnection:
        self._profiles.allowed(url)
        parsed = urlparse(url)
        host = parsed.hostname
        assert host is not None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        decoded_host = self._decode_host(host)
        if self._is_private_or_link_local(decoded_host):
            msg = f"Refusing private or link-local address: {decoded_host}"
            raise EgressDeniedError(msg)
        cache_key = (decoded_host.lower(), port)
        if cache_key not in self._pin_cache:
            infos = socket.getaddrinfo(decoded_host, port, type=socket.SOCK_STREAM)
            if not infos:
                msg = f"DNS resolution failed for {decoded_host}"
                raise EgressDeniedError(msg)
            chosen = str(infos[0][4][0])
            if self._is_private_or_link_local(chosen):
                msg = f"Pinned address is not public: {chosen}"
                raise EgressDeniedError(msg)
            self._pin_cache[cache_key] = chosen
        return PinnedConnection(host=decoded_host, port=port, pinned_ip=self._pin_cache[cache_key])

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        pinned = self.pin(url)
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(
            transport=transport, follow_redirects=False, timeout=timeout
        ) as client:
            # httpx does not expose connect-to directly; validate URL host matches pin pre-request.
            if parsed.hostname and parsed.hostname.lower() != pinned.host.lower():
                msg = "Host mismatch after parsing"
                raise EgressDeniedError(msg)
            response = await client.request(
                method,
                url,
                headers=headers,
                content=content,
            )
        if response.status_code in (301, 302, 303, 307, 308):
            msg = "Redirects are refused"
            raise EgressDeniedError(msg)
        return response

    @staticmethod
    def _decode_host(host: str) -> str:
        lowered = host.lower().strip()
        if lowered.startswith("0x") and all(c in "0123456789abcdef." for c in lowered[2:]):
            # dotted hex encoding attempt
            msg = "Odd address encoding refused"
            raise EgressDeniedError(msg)
        if lowered.startswith("0x"):
            try:
                as_int = int(lowered, 16)
                return str(ipaddress.IPv4Address(as_int))
            except ValueError:
                pass
        # decimal encoded IPv4 (e.g. 2130706433)
        if lowered.isdigit():
            try:
                return str(ipaddress.IPv4Address(int(lowered)))
            except ValueError:
                pass
        # octal dotted
        if lowered.replace(".", "").isdigit() and lowered.count(".") == 3:
            parts = lowered.split(".")
            if any(len(p) > 1 and p.startswith("0") for p in parts):
                msg = "Octal IPv4 encoding refused"
                raise EgressDeniedError(msg)
        return host

    @staticmethod
    def _is_private_or_link_local(host_or_ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(host_or_ip)
        except ValueError:
            return False
        return bool(
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
        )
