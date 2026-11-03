from __future__ import annotations

from cleartrace_core_api.errors import problem_response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Ensure POST requests declare an idempotency key (except health/docs)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/systems")
            and not request.headers.get("Idempotency-Key")
        ):
            return problem_response(
                status=400,
                title="Missing idempotency key",
                detail="Idempotency-Key header is required for POST /systems",
            )
        return await call_next(request)
