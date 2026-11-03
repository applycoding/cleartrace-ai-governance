from __future__ import annotations

from typing import Any
from uuid import UUID

from cleartrace_reports.models import ReportFormat
from cleartrace_reports.service import ReportService
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from cleartrace_core_api.errors import problem_response

router = APIRouter(prefix="/reports", tags=["reports"])

_service = ReportService()
_artifacts: dict[str, dict[str, Any]] = {}


class ReportCreate(BaseModel):
    type: str = Field(default="system_dossier", max_length=64)
    scope: dict[str, Any] = Field(default_factory=dict)
    language: str = Field(default="en-CA", pattern=r"^(en|fr)(-CA)?$")
    format: ReportFormat = ReportFormat.HTML


@router.post("", status_code=202)
async def create_report(request: Request, body: ReportCreate) -> dict[str, str]:
    auth = request.state.auth
    spec: dict[str, object] = {
        "type": body.type,
        "scope": body.scope,
        "language": body.language,
        "format": body.format.value,
    }
    artefact = _service.build_sync(auth.tenant_id, spec)
    _artifacts[str(artefact.report_id)] = {
        "tenant_id": str(auth.tenant_id),
        "content_type": artefact.content_type,
        "filename": artefact.filename,
        "body": artefact.body,
    }
    return {"id": str(artefact.report_id), "status": "completed"}


@router.get("/{report_id}")
async def get_report(report_id: UUID, request: Request) -> Response:
    auth = request.state.auth
    stored = _artifacts.get(str(report_id))
    # Reports belong to the tenant that built them; another tenant's id is a 404.
    if stored is None or stored.get("tenant_id") != str(auth.tenant_id):
        return problem_response(status=404, title="Not found", detail="Report not found")
    return Response(
        content=stored["body"],
        media_type=str(stored["content_type"]),
        headers={"Content-Disposition": f'attachment; filename="{stored["filename"]}"'},
    )
