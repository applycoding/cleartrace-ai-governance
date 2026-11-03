from __future__ import annotations

from typing import Any

import httpx


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """Connect to a pre-resolved IP while sending the original Host header."""

    def __init__(
        self,
        *,
        pinned_ip: str,
        host_header: str,
        port: int,
        use_tls: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._pinned_ip = pinned_ip
        self._host_header = host_header
        self._port = port
        self._use_tls = use_tls

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        pinned_url = request.url.copy_with(host=self._pinned_ip, port=self._port)
        pinned_request = httpx.Request(
            request.method,
            pinned_url,
            headers={**request.headers, "Host": self._host_header},
            content=request.content,
        )
        if self._use_tls:
            pinned_request.extensions["sni_hostname"] = self._host_header
        return await super().handle_async_request(pinned_request)
