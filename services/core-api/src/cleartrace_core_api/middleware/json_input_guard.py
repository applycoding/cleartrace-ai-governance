"""Reject request input carrying NUL characters (ASVS V5.1.3, V5.1.4).

PostgreSQL text and jsonb cannot store U+0000, so such input would otherwise fail
deep in a handler as a 500. It is never valid data for this API.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import unquote

from cleartrace_core_api.errors import problem_response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def _has_nul(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_has_nul(k) or _has_nul(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_has_nul(v) for v in value)
    return False


class JsonInputGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if "\x00" in request.url.path or "\x00" in unquote(request.url.query):
            return problem_response(
                status=422,
                title="Validation failed",
                detail="URL path and query must not contain NUL (U+0000) characters",
                instance=None,
            )
        content_type = request.headers.get("content-type", "")
        if request.method in {"POST", "PUT", "PATCH"} and "json" in content_type:
            body = await request.body()
            if b"\\u0000" in body:
                try:
                    parsed = json.loads(body)
                except ValueError:
                    parsed = None
                if parsed is not None and _has_nul(parsed):
                    return problem_response(
                        status=422,
                        title="Validation failed",
                        detail="JSON strings must not contain NUL (U+0000) characters",
                        instance=str(request.url.path),
                    )
        return await call_next(request)
