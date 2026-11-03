from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cleartrace_register.categories import GOVERNANCE_CATEGORIES
from cleartrace_register.csv_import import RegisterStore, bind_system_ids, parse_gc_ai_register_csv
from fastapi import APIRouter
from pydantic import BaseModel
from uuid6 import uuid7

router = APIRouter(prefix="/register", tags=["register"])

_store = RegisterStore()


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
async def get_system_register(system_id: UUID, system_key: str = "unknown") -> SystemRegisterView:
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
async def import_gc_register(body: ImportCsvRequest) -> ImportCsvResponse:
    updates = parse_gc_ai_register_csv(body.csv_content)
    key_to_id: dict[str, UUID] = {}
    for update in updates:
        if update.category_number == 1 and update.value_en:
            key = update.value_en.lower().replace(" ", "-")[:64]
            if key not in key_to_id:
                system_id = uuid7()
                key_to_id[key] = system_id
                _store.register_system(system_id, key)
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
    def include_router(self, router: APIRouter, /) -> None: ...


def mount_register_routes(app: _RouterHost) -> None:
    app.include_router(router)
