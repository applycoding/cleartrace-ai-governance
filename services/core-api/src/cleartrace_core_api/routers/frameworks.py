from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_engine.framework_studio import list_packs, load_pack, pack_to_oscal_catalog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from cleartrace_core_api.framework.lifecycle import (
    AssignmentRecord,
    FrameworkLifecycle,
)

router = APIRouter(prefix="/frameworks", tags=["frameworks"])

_PACKS_ROOT = Path(__file__).resolve().parents[5] / "policies" / "packs"
_lifecycle = FrameworkLifecycle()


class FrameworkPackSummary(BaseModel):
    slug: str
    name_en: str
    name_fr: str
    obligation_type: str
    needs_second_reader_recheck: bool = True


class AssignmentCreate(BaseModel):
    """Exactly one of ai_system_id or group_id; unknown keys are refused (closed shapes)."""

    model_config = ConfigDict(extra="forbid")

    framework_version_id: UUID
    ai_system_id: UUID | None = None
    group_id: UUID | None = None
    criteria_overrides: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_framework_packs() -> list[FrameworkPackSummary]:
    summaries: list[FrameworkPackSummary] = []
    for path in list_packs(_PACKS_ROOT):
        pack = load_pack(path)
        summaries.append(
            FrameworkPackSummary(
                slug=pack["slug"],
                name_en=pack["name_en"],
                name_fr=pack["name_fr"],
                obligation_type=pack["obligation_type"],
                needs_second_reader_recheck=bool(pack.get("needs_second_reader_recheck")),
            )
        )
    return summaries


@router.get("/packs/{slug}/oscal")
def export_pack_oscal(slug: str) -> dict[str, Any]:
    path = _PACKS_ROOT / slug / "pack.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = load_pack(path)
    if pack["slug"] != slug:
        raise HTTPException(status_code=400, detail="Pack slug mismatch")
    return pack_to_oscal_catalog(pack)


@router.post("/assignments")
def create_assignment(body: AssignmentCreate) -> dict[str, str]:
    import uuid

    targets = {"ai_system_id", "group_id"} & body.model_fields_set
    if len(targets) != 1 or bool(body.ai_system_id) == bool(body.group_id):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of ai_system_id or group_id",
        )
    record = AssignmentRecord(
        id=uuid.uuid4(),
        framework_version_id=body.framework_version_id,
        ai_system_id=body.ai_system_id,
        group_id=body.group_id,
        criteria_overrides=body.criteria_overrides,
    )
    _lifecycle.add_assignment(record)
    return {"id": str(record.id)}


@router.get("/reassessment-flags")
def list_reassessment_flags() -> list[dict[str, Any]]:
    return _lifecycle.reassessment_flags()


def get_framework_lifecycle() -> FrameworkLifecycle:
    return _lifecycle
