from __future__ import annotations

import re

from cleartrace_core_api.errors import problem_response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

MAX_KEY_LENGTH = 128
_KEY_PATTERN = re.compile(rf"[!-~]{{1,{MAX_KEY_LENGTH}}}")


def _has_post_route(request: Request) -> bool:
    """True when a route accepts POST on this exact path (method included)."""
    router = getattr(request.app, "router", None)
    for route in getattr(router, "routes", []):
        match, _ = route.matches(request.scope)
        if match is Match.FULL:
            return True
    return False


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Ensure POST requests under /systems declare an idempotency key.

    Only applies where a POST route exists, so a POST to a GET-only path still
    gets the router's 405 with an ``Allow`` header.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method == "POST"
            and request.url.path.startswith("/api/v1/systems")
            and not request.headers.get("Idempotency-Key")
            and _has_post_route(request)
        ):
            return problem_response(
                status=400,
                title="Missing idempotency key",
                detail="Idempotency-Key header is required for POST /systems",
            )
        key = request.headers.get("Idempotency-Key")
        if key is not None and _KEY_PATTERN.fullmatch(key) is None:
            return problem_response(
                status=400,
                title="Invalid idempotency key",
                detail=(
                    f"Idempotency-Key must be 1 to {MAX_KEY_LENGTH} visible ASCII characters"
                    " with no spaces"
                ),
            )
        return await call_next(request)
