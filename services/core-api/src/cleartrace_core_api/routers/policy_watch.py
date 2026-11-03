from __future__ import annotations

from uuid import UUID

from cleartrace_policy_watch.service import PolicyWatcherService
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["policy-watch"])

_watcher = PolicyWatcherService()


class PolicySource(BaseModel):
    slug: str
    locale: str


class CaptureBody(BaseModel):
    policy_slug: str
    locale: str
    html: str


@router.get("/policy-sources")
async def list_policy_sources() -> dict[str, list[PolicySource]]:
    return {
        "items": [
            PolicySource(slug="dadm", locale="en-CA"),
            PolicySource(slug="dadm", locale="fr-CA"),
        ]
    }


@router.get("/policy-diffs")
async def list_policy_diffs() -> dict[str, list[dict[str, str]]]:
    items = [
        {
            "id": str(record.diff_id),
            "policy_slug": record.policy_slug,
            "substantive_count": str(record.result.substantive_count),
            "activated": str(record.activated),
        }
        for record in _watcher.list_diff_records()
    ]
    return {"items": items}


@router.post("/policy-diffs/{diff_id}:promote")
async def promote_policy_diff(diff_id: UUID, request: Request) -> dict[str, str]:
    _ = request
    record = _watcher.get_diff(diff_id)
    if record is None:
        return {"status": "not_found"}
    _watcher.approve_by_steward(diff_id)
    _watcher.activate(diff_id)
    return {"id": str(diff_id), "status": "activated"}


@router.get("/impact-sets/{impact_id}")
async def get_impact_set(impact_id: UUID) -> dict[str, object]:
    record = _watcher.get_diff(impact_id)
    if record is None:
        return {"systems": [], "controls": []}
    return {
        "id": str(impact_id),
        "systems": [str(s) for s in record.impact_system_ids],
        "controls": list(record.impact_control_ids),
    }


@router.post("/policy-diffs/capture")
async def capture_policy_diff(body: CaptureBody) -> dict[str, str]:
    record = _watcher.diff_against_active(body.policy_slug, body.locale, body.html)
    return {"diff_id": str(record.diff_id)}
