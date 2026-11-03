from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import BaseModel, Field
from uuid6 import uuid7

from cleartrace_core_api.errors import problem_response
from cleartrace_core_api.pagination import decode_cursor, encode_cursor

router = APIRouter(prefix="/systems", tags=["systems"])

_store: dict[str, dict[str, object]] = {}
_etags: dict[str, str] = {}


class SystemSummary(BaseModel):
    id: UUID
    system_key: str
    name_en: str
    name_fr: str


class SystemPage(BaseModel):
    items: list[SystemSummary]
    next_cursor: str | None = None


class CreateSystemRequest(BaseModel):
    system_key: str = Field(min_length=1, max_length=64)
    name_en: str
    name_fr: str


@router.get("", response_model=SystemPage)
async def list_systems(
    request: Request,
    response: Response,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
) -> SystemPage:
    _ = accept_language
    auth = request.state.auth
    tenant_key = str(auth.tenant_id)
    items = [
        SystemSummary.model_validate(v) for v in _store.values() if v.get("tenant_id") == tenant_key
    ]
    start = decode_cursor(cursor) if cursor else 0
    page = items[start : start + limit]
    next_cursor = encode_cursor(start + limit) if start + limit < len(items) else None
    response.headers["Cache-Control"] = "no-store"
    return SystemPage(items=page, next_cursor=next_cursor)


@router.post("", status_code=201, response_model=SystemSummary)
async def create_system(
    request: Request,
    body: CreateSystemRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SystemSummary | Response:
    auth = request.state.auth
    if idempotency_key:
        cached = _store.get(f"idempotency:{idempotency_key}")
        if cached:
            summary = SystemSummary.model_validate(cached["resource"])
            return summary
    system_id = uuid7()
    record = {
        "id": system_id,
        "tenant_id": str(auth.tenant_id),
        "system_key": body.system_key,
        "name_en": body.name_en,
        "name_fr": body.name_fr,
    }
    _store[str(system_id)] = record
    if idempotency_key:
        _store[f"idempotency:{idempotency_key}"] = {"resource": record}
    summary = SystemSummary(
        id=system_id,
        system_key=body.system_key,
        name_en=body.name_en,
        name_fr=body.name_fr,
    )
    _etags[str(system_id)] = f'W/"{system_id}"'
    return summary


@router.patch("/{system_id}", response_model=SystemSummary)
async def patch_system(
    system_id: UUID,
    request: Request,
    body: CreateSystemRequest,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> SystemSummary | Response:
    key = str(system_id)
    record = _store.get(key)
    if not record:
        return problem_response(status=404, title="Not found", detail="System not found")
    current = _etags.get(key)
    if if_match is None or if_match != current:
        return problem_response(
            status=428,
            title="Precondition Required",
            detail="If-Match header must match the current ETag",
        )
    record.update(
        {
            "system_key": body.system_key,
            "name_en": body.name_en,
            "name_fr": body.name_fr,
        }
    )
    new_tag = f'W/"{uuid7()}"'
    _etags[key] = new_tag
    summary = SystemSummary.model_validate(record)
    return summary
