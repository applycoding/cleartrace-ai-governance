from __future__ import annotations

from typing import Any
from uuid import UUID

from cleartrace_reports.service import ReportService
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/reports", tags=["reports"])

_service = ReportService()
_artifacts: dict[str, dict[str, Any]] = {}


class ReportCreate(BaseModel):
    type: str = Field(default="system_dossier")
    scope: dict[str, Any] = Field(default_factory=dict)
    language: str = "en-CA"
    format: str = "html"


@router.post("", status_code=202)
async def create_report(request: Request, body: ReportCreate) -> dict[str, str]:
    auth = request.state.auth
    spec: dict[str, object] = {
        "type": body.type,
        "scope": body.scope,
        "language": body.language,
        "format": body.format,
    }
    artefact = _service.build_sync(auth.tenant_id, spec)
    _artifacts[str(artefact.report_id)] = {
        "content_type": artefact.content_type,
        "filename": artefact.filename,
        "body": artefact.body,
    }
    return {"id": str(artefact.report_id), "status": "completed"}


@router.get("/{report_id}")
async def get_report(report_id: UUID) -> Response:
    stored = _artifacts.get(str(report_id))
    if stored is None:
        return Response(status_code=404, content=b"report not found")
    return Response(
        content=stored["body"],
        media_type=str(stored["content_type"]),
        headers={"Content-Disposition": f'inline; filename="{stored["filename"]}"'},
    )
