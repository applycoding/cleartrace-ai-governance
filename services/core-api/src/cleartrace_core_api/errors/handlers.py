from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cleartrace_core_api.errors.problem import problem_response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem_response(
            status=exc.status_code,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            detail=str(exc.detail),
            instance=str(request.url.path),
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
