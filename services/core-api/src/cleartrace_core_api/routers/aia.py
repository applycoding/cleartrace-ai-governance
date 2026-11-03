from __future__ import annotations

from typing import Any
from uuid import UUID

from cleartrace_aia.scorer import AIAEngineService
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["aia"])

_engine = AIAEngineService()


class AiaScoreRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)


@router.get("/aia/schema")
async def aia_schema() -> dict[str, str]:
    return {"version": "b625733", "pinned_commit": "b625733"}


@router.post("/aia:score")
async def aia_score(body: AiaScoreRequest) -> dict[str, Any]:
    return await _engine.score_answers(body.answers)


@router.post("/systems/{system_id}/aia")
async def post_system_aia(system_id: UUID, body: AiaScoreRequest) -> dict[str, Any]:
    _ = system_id
    return await _engine.score_answers(body.answers)


@router.get("/aia/{record_id}/export")
async def export_aia(record_id: UUID, request: Request) -> dict[str, str]:
    _ = request
    return {"record_id": str(record_id), "format": "json", "status": "ready"}
