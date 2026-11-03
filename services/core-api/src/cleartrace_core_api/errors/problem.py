from __future__ import annotations

from typing import Any

from cleartrace_contracts.models import ProblemDetail
from fastapi.responses import JSONResponse


def problem_response(
    *,
    status: int,
    title: str,
    detail: str | None = None,
    type_uri: str = "about:blank",
    instance: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ProblemDetail(
        type=type_uri,
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        errors=errors,
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(exclude_none=True),
        media_type="application/problem+json",
        headers=headers,
    )
