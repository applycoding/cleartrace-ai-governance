from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class OptimisticLockMiddleware(BaseHTTPMiddleware):
    """Attach ETag header on GET single-resource responses when available."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        etag = getattr(request.state, "etag", None)
        if etag:
            response.headers["ETag"] = etag
        return response
