from __future__ import annotations

from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from cleartrace_evidence.reviewer import LifecycleState
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from uuid6 import uuid7

from cleartrace_core_api.deps import get_audit_ledger, get_reviewer
from cleartrace_core_api.errors import problem_response

router = APIRouter(tags=["assessments"])

_jobs: dict[str, dict[str, Any]] = {}


class StartAssessmentRequest(BaseModel):
    ai_system_id: UUID
    framework_version_id: UUID | None = None
    pack_slug: str = Field(default="dadm", min_length=1)


class AssessmentJob(BaseModel):
    id: UUID
    status: str
    finding_id: UUID | None = None


@router.post("/assessments", status_code=202, response_model=AssessmentJob)
async def start_assessment(request: Request, body: StartAssessmentRequest) -> AssessmentJob | object:
    auth = request.state.auth
    settings = request.app.state.settings
    job_id = uuid7()
    reviewer = get_reviewer(request)
    ledger = get_audit_ledger(request)
    def audit_append(
        conn: object,
        *,
        tenant_id: UUID,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        payload: dict[str, object],
    ) -> None:
        ledger.append_event_tx(
            conn,  # type: ignore[arg-type]
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )

    try:
        with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
            finding_id = reviewer.create_finding(
                conn,
                tenant_id=auth.tenant_id,
                ai_system_id=body.ai_system_id,
                control_id=f"ASSESS-{body.pack_slug}",
                lifecycle_state=LifecycleState.DRAFT_AUTO,
                outcome_state="not_met",
                certainty_index=0.82,
            )
            audit_append(
                conn,
                tenant_id=auth.tenant_id,
                actor_id=UUID(str(auth.raw_claims.get("principal_id") or auth.subject)),
                action="assessment.started",
                resource_type="assessment_job",
                resource_id=job_id,
                payload={"pack_slug": body.pack_slug, "finding_id": str(finding_id)},
            )
    except Exception as exc:
        return problem_response(
            status=400,
            title="Assessment failed",
            detail=str(exc),
        )

    job = AssessmentJob(id=job_id, status="completed", finding_id=finding_id)
    _jobs[str(job_id)] = job.model_dump()
    return job


@router.get("/assessments/{job_id}", response_model=AssessmentJob)
async def get_assessment(job_id: UUID) -> AssessmentJob | object:
    raw = _jobs.get(str(job_id))
    if raw is None:
        return problem_response(status=404, title="Not found", detail="Assessment job not found")
    return AssessmentJob.model_validate(raw)
