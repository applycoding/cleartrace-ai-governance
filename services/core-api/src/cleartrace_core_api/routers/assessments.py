from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control_with_index
from cleartrace_evidence.reviewer import LifecycleState
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from uuid6 import uuid7

from cleartrace_core_api.deps import get_audit_ledger, get_reviewer
from cleartrace_core_api.errors import problem_response

router = APIRouter(tags=["assessments"])

_jobs: dict[str, dict[str, Any]] = {}

_PACKS_ROOT = Path(__file__).resolve().parents[5] / "policies" / "packs"


class StartAssessmentRequest(BaseModel):
    ai_system_id: UUID
    framework_version_id: UUID | None = None
    pack_slug: str = Field(
        default="dadm", min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$"
    )
    control_key: str | None = None
    system_profile: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AssessmentJob(BaseModel):
    id: UUID
    status: str
    finding_id: UUID | None = None
    outcome_state: str | None = None
    reason_code: str | None = None
    certainty_index: float | None = None


def _run_pack_assessment(body: StartAssessmentRequest) -> tuple[str, str, float, str]:
    pack_path = (_PACKS_ROOT / body.pack_slug / "pack.yaml").resolve()
    if not pack_path.is_relative_to(_PACKS_ROOT.resolve()) or not pack_path.is_file():
        msg = f"Unknown policy pack: {body.pack_slug}"
        raise ValueError(msg)
    pack = load_pack(pack_path)
    controls = pack["controls"]
    if not controls:
        raise ValueError(f"Pack {body.pack_slug} has no controls")
    if body.control_key:
        control = next((c for c in controls if c["control_key"] == body.control_key), None)
        if control is None:
            raise ValueError(f"Control {body.control_key} not found in pack {body.pack_slug}")
    else:
        control = controls[0]
    system = dict(body.system_profile)
    output, _ctx, certainty = assess_pack_control_with_index(
        pack=pack,
        control=control,
        system=system,
        evidence=body.evidence,
        pack_slug=body.pack_slug,
        cel_context=system,
    )
    control_id = str(control["control_key"])
    return output.outcome_state, output.reason_code, certainty, control_id


@router.post("/assessments", status_code=202, response_model=AssessmentJob)
async def start_assessment(
    request: Request, body: StartAssessmentRequest
) -> AssessmentJob | object:
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
        outcome_state, reason_code, certainty, control_id = _run_pack_assessment(body)
        with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
            # RLS limits this lookup to the caller's tenant, so another tenant's
            # system id is treated the same as an unknown one.
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM ai_system WHERE id = %s", (body.ai_system_id,))
                system_visible = cur.fetchone() is not None
            if not system_visible:
                return problem_response(
                    status=404, title="Not found", detail="AI system not found"
                )
            finding_id = reviewer.create_finding(
                conn,
                tenant_id=auth.tenant_id,
                ai_system_id=body.ai_system_id,
                control_id=control_id,
                lifecycle_state=LifecycleState.DRAFT_AUTO,
                outcome_state=outcome_state,
                certainty_index=certainty,
                reason_code=reason_code,
            )
            audit_append(
                conn,
                tenant_id=auth.tenant_id,
                actor_id=auth.actor_id,
                action="assessment.started",
                resource_type="assessment_job",
                resource_id=job_id,
                payload={
                    "pack_slug": body.pack_slug,
                    "finding_id": str(finding_id),
                    "outcome_state": outcome_state,
                },
            )
    except ValueError as exc:
        # Unknown pack/control or invalid input. Engine or database outages are not
        # caught here so they surface as server errors instead of client errors.
        return problem_response(
            status=400,
            title="Assessment failed",
            detail=str(exc),
        )

    job = AssessmentJob(
        id=job_id,
        status="completed",
        finding_id=finding_id,
        outcome_state=outcome_state,
        reason_code=reason_code,
        certainty_index=certainty,
    )
    _jobs[str(job_id)] = {"tenant_id": str(auth.tenant_id), **job.model_dump()}
    return job


@router.get("/assessments/{job_id}", response_model=AssessmentJob)
async def get_assessment(job_id: UUID, request: Request) -> AssessmentJob | object:
    raw = _jobs.get(str(job_id))
    # Jobs are visible only to the tenant that ran them.
    if raw is None or raw.get("tenant_id") != str(request.state.auth.tenant_id):
        return problem_response(status=404, title="Not found", detail="Assessment job not found")
    return AssessmentJob.model_validate(raw)
