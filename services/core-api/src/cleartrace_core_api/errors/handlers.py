from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cleartrace_core_api.errors.problem import problem_response

_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}


def _allowed_methods(request: Request) -> str | None:
    """Methods the documented API accepts on this path, for the 405 ``Allow``.

    Starlette answers 405 from the first route whose path matches, so a path
    served by separate GET and POST routes would only advertise one of them.
    The OpenAPI document is the contract, so the union is taken from it.
    """
    app = request.app
    table = getattr(app.state, "allow_table", None)
    if table is None:
        table = []
        for template, item in app.openapi().get("paths", {}).items():
            pattern = re.sub(r"\\{[^}/]+\\}", "[^/]+", re.escape(template))
            methods = {m.upper() for m in item if m in _HTTP_METHODS}
            if "GET" in methods:
                methods.add("HEAD")
            table.append((re.compile(f"^{pattern}$"), methods))
        app.state.allow_table = table
    allowed: set[str] = set()
    for pattern, methods in table:
        if pattern.match(request.url.path):
            allowed |= methods
    return ", ".join(sorted(allowed)) if allowed else None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        headers = dict(exc.headers) if exc.headers else {}
        if exc.status_code == 405:
            allow = _allowed_methods(request)
            if allow:
                headers["Allow"] = allow
        return problem_response(
            status=exc.status_code,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            detail=str(exc.detail),
            instance=str(request.url.path),
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response(
            status=422,
            title="Validation failed",
            detail="Request validation failed",
            instance=str(request.url.path),
            errors=[{"msg": e["msg"], "loc": list(e["loc"])} for e in exc.errors()],
        )
