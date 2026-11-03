from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class LanguageMiddleware(BaseHTTPMiddleware):
    """Parse Accept-Language (en-CA / fr-CA) for downstream handlers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        header = request.headers.get("Accept-Language", "en-CA")
        primary = header.split(",")[0].strip()
        if primary not in {"en-CA", "fr-CA"}:
            primary = "en-CA"
        request.state.locale = primary
        response = await call_next(request)
        response.headers.setdefault("Content-Language", primary)
        return response
