from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from cleartrace_core_api.auth.context import AuthContext
from cleartrace_core_api.config import Settings
from cleartrace_core_api.errors import problem_response
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class _TenantRateLimiter:
    """In-process sliding-window limiter keyed by tenant (per API process)."""

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, tenant_key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._events[tenant_key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = max(1, int(self._window - (now - bucket[0])) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0


_limiter: _TenantRateLimiter | None = None


def _limiter_for(settings: Settings) -> _TenantRateLimiter:
    global _limiter
    if _limiter is None or _limiter._limit != settings.tenant_rate_limit_per_window:
        _limiter = _TenantRateLimiter(
            limit=settings.tenant_rate_limit_per_window,
            window_seconds=float(settings.tenant_rate_limit_window_seconds),
        )
    return _limiter


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant request rate limits (blueprint noisy-neighbour controls)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings: Settings = request.app.state.settings
        if settings.tenant_rate_limit_per_window <= 0:
            return await call_next(request)
        public_paths = {
            "/api/v1/health",
            "/api/v1/openapi.json",
            "/api/v1/docs",
            "/api/v1/capabilities",
        }
        if request.url.path in public_paths:
            return await call_next(request)
        auth: AuthContext | None = getattr(request.state, "auth", None)
        if auth is None:
            return await call_next(request)
        limiter = _limiter_for(settings)
        allowed, retry_after = limiter.allow(str(auth.tenant_id))
        if not allowed:
            return problem_response(
                status=429,
                title="Too Many Requests",
                detail="Per-tenant rate limit exceeded",
                type_uri="https://cleartrace.local/problems/rate-limit",
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
