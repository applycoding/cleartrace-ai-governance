from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class DestinationProfile:
    host: str
    port: int
    cidr: str | None = None
    mtls_required: bool = False

    def matches_host(self, host: str) -> bool:
        normalized = host.lower().rstrip(".")
        if normalized == self.host.lower().rstrip("."):
            return True
        if self.cidr:
            try:
                net = ipaddress.ip_network(self.cidr, strict=False)
                addr = ipaddress.ip_address(normalized)
                return addr in net
            except ValueError:
                return False
        return False


class DestinationProfileSet:
    def __init__(self, profiles: list[DestinationProfile]) -> None:
        self._profiles = profiles

    def allowed(self, url: str) -> DestinationProfile:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            msg = f"Unsupported scheme: {parsed.scheme}"
            raise EgressDeniedError(msg)
        host = parsed.hostname
        if host is None:
            msg = "Missing hostname"
            raise EgressDeniedError(msg)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if self._is_blocked_platform(host):
            msg = f"Blocked platform endpoint: {host}"
            raise EgressDeniedError(msg)
        for profile in self._profiles:
            if profile.port == port and profile.matches_host(host):
                return profile
        msg = f"Destination not in approved profile: {host}:{port}"
        raise EgressDeniedError(msg)

    @staticmethod
    def _is_blocked_platform(host: str) -> bool:
        blocked_suffixes = (
            ".amazonaws.com",
            ".googleapis.com",
            "169.254.169.254",
            "metadata.google.internal",
        )
        lowered = host.lower()
        if lowered.rstrip(".") == "localhost":
            return True
        try:
            addr = ipaddress.ip_address(lowered.strip("[]"))
        except ValueError:
            addr = None
        if addr is not None:
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
                addr = addr.ipv4_mapped
            if addr.is_loopback or addr.is_unspecified or addr.is_link_local:
                return True
        return any(
            lowered.endswith(suffix) or lowered == suffix.rstrip(".") for suffix in blocked_suffixes
        )


class EgressDeniedError(Exception):
    """Raised when a connector attempts a disallowed egress destination."""
