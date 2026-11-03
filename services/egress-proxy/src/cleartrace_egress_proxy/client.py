from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from cleartrace_egress_proxy.profiles import DestinationProfileSet, EgressDeniedError
from cleartrace_egress_proxy.transport import PinnedAsyncHTTPTransport


@dataclass(frozen=True, slots=True)
class PinnedConnection:
    host: str
    port: int
    pinned_ip: str


class EgressClient:
    """Resolve DNS once, validate all answers, pin connect to one public address."""

    METADATA_HOSTS = frozenset(
        {
            "169.254.169.254",
            "metadata.google.internal",
            "metadata.goog",
        }
    )

    def __init__(self, profiles: DestinationProfileSet) -> None:
        self._profiles = profiles
        self._pin_cache: dict[tuple[str, int], str] = {}

    def pin(self, url: str) -> PinnedConnection:
        self._profiles.allowed(url)
        parsed = urlparse(url)
        host = parsed.hostname
        if host is None:
            msg = "Missing hostname"
            raise EgressDeniedError(msg)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        decoded_host = self._decode_host(host)
        if self._is_blocked_host(decoded_host):
            msg = f"Blocked host: {decoded_host}"
            raise EgressDeniedError(msg)
        cache_key = (decoded_host.lower(), port)
        if cache_key not in self._pin_cache:
            self._pin_cache[cache_key] = self._resolve_and_pin(decoded_host, port)
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
        use_tls = parsed.scheme == "https"
        transport = PinnedAsyncHTTPTransport(
            pinned_ip=pinned.pinned_ip,
            host_header=pinned.host,
            port=pinned.port,
            use_tls=use_tls,
        )
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            timeout=timeout,
            verify=ssl.create_default_context() if use_tls else False,
        ) as client:
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

    def _resolve_and_pin(self, host: str, port: int) -> str:
        try:
            addr = ipaddress.ip_address(host)
            addresses = [addr]
        except ValueError:
            try:
                infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                msg = f"DNS resolution failed for {host}"
                raise EgressDeniedError(msg) from exc
            addresses = []
            for info in infos:
                ip_str = str(info[4][0])
                addresses.append(ipaddress.ip_address(ip_str))

        for addr in addresses:
            if self._is_blocked_address(addr):
                msg = f"Resolved blocked address for {host}: {addr}"
                raise EgressDeniedError(msg)

        chosen = addresses[0]
        return str(chosen)

    def _is_blocked_host(self, host: str) -> bool:
        lowered = host.lower().rstrip(".")
        if lowered in self.METADATA_HOSTS:
            return True
        try:
            return self._is_blocked_address(ipaddress.ip_address(lowered))
        except ValueError:
            return False

    @staticmethod
    def _is_blocked_address(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            return True
        if addr.is_multicast or addr.is_reserved:
            return True
        return str(addr) == "169.254.169.254"

    @staticmethod
    def _decode_host(host: str) -> str:
        lowered = host.lower().strip()
        if lowered.startswith("[") and lowered.endswith("]"):
            lowered = lowered[1:-1]
        if lowered.startswith("0x") and "." in lowered:
            msg = "Odd address encoding refused"
            raise EgressDeniedError(msg)
        if lowered.startswith("0x"):
            try:
                return str(ipaddress.IPv4Address(int(lowered, 16)))
            except ValueError:
                pass
        if lowered.isdigit():
            try:
                return str(ipaddress.IPv4Address(int(lowered)))
            except ValueError:
                pass
        if lowered.count(".") == 3:
            parts = lowered.split(".")
            if any(len(p) > 1 and p.startswith("0") for p in parts):
                msg = "Octal IPv4 encoding refused"
                raise EgressDeniedError(msg)
        if lowered.startswith("::ffff:"):
            mapped = lowered.removeprefix("::ffff:")
            try:
                return str(ipaddress.IPv4Address(mapped))
            except ValueError:
                pass
        return host
