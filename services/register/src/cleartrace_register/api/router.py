from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cleartrace_register.categories import GOVERNANCE_CATEGORIES
from cleartrace_register.csv_import import (
    RegisterCsvError,
    bind_system_ids,
    parse_gc_ai_register_csv,
)
from cleartrace_register.memory_store import MemoryRegisterStore
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from uuid6 import uuid7

router = APIRouter(prefix="/register", tags=["register"])

_store = MemoryRegisterStore()
# Systems created by a CSV import belong to the importing tenant.
_system_tenant: dict[UUID, str] = {}


def _tenant_of(request: Request) -> str | None:
    auth = getattr(request.state, "auth", None)
    return str(auth.tenant_id) if auth is not None else None


class CategoryStatus(BaseModel):
    number: int
    slug: str
    name_en: str
    name_fr: str
    filled: bool


class SystemRegisterView(BaseModel):
    system_id: UUID
    system_key: str
    categories: list[CategoryStatus]


class ImportCsvRequest(BaseModel):
    csv_content: str


class ImportCsvResponse(BaseModel):
    systems_updated: int
    fields_applied: int


@router.get("/systems/{system_id}", response_model=SystemRegisterView)
async def get_system_register(
    system_id: UUID, request: Request, system_key: str = "unknown"
) -> SystemRegisterView:
    owner = _system_tenant.get(system_id)
    if owner is not None and owner != _tenant_of(request):
        raise HTTPException(status_code=404, detail="System not found")
    categories = [
        CategoryStatus(
            number=cat.number,
            slug=cat.slug,
            name_en=cat.name_en,
            name_fr=cat.name_fr,
            filled=_store.category_filled(system_id, cat.number),
        )
        for cat in GOVERNANCE_CATEGORIES
    ]
    return SystemRegisterView(system_id=system_id, system_key=system_key, categories=categories)


@router.post("/import/gc-ai-register", response_model=ImportCsvResponse)
async def import_gc_register(body: ImportCsvRequest, request: Request) -> ImportCsvResponse:
    try:
        updates = parse_gc_ai_register_csv(body.csv_content)
    except RegisterCsvError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    tenant = _tenant_of(request)
    key_to_id: dict[str, UUID] = {}
    for update in updates:
        if update.category_number == 1 and update.value_en:
            key = update.value_en.lower().replace(" ", "-")[:64]
            if key not in key_to_id:
                system_id = uuid7()
                key_to_id[key] = system_id
                _store.register_system(system_id, key)
                if tenant is not None:
                    _system_tenant[system_id] = tenant
    bound = bind_system_ids(updates, key_to_id)
    applied = 0
    for update in bound:
        before = _store.engine.get_value(update.system_id, update.category_number, update.slot_key)
        _store.ingest(update)
        after = _store.engine.get_value(update.system_id, update.category_number, update.slot_key)
        if before != after:
            applied += 1
    return ImportCsvResponse(systems_updated=len(key_to_id), fields_applied=applied)


class _RouterHost(Protocol):
    def include_router(self, router: APIRouter, /, *, prefix: str = "") -> None: ...


def mount_register_routes(app: _RouterHost, *, prefix: str = "") -> None:
    app.include_router(router, prefix=prefix)
