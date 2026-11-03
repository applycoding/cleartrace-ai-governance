from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from cleartrace_evidence.reviewer import ReviewAction, SeparationOfDutiesError, StaleFindingError
from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

from cleartrace_core_api.deps import get_audit_ledger, get_reviewer
from cleartrace_core_api.errors import problem_response

router = APIRouter(prefix="/findings", tags=["assessments"])


class ReviewActionRequest(BaseModel):
    action: Literal["validate", "reject", "modify", "annotate"]
    reason_code: str | None = None
    rationale_en: str | None = None
    rationale_fr: str | None = None
    modified_outcome: str | None = None


class ReviewActionResponse(BaseModel):
    finding_id: UUID
    etag: str
    lifecycle_state: str
    outcome_state: str


class FindingSummary(BaseModel):
    id: UUID
    etag: str
    control_id: str
    lifecycle_state: str
    outcome_state: str


@router.get("/{finding_id}", response_model=FindingSummary)
async def get_finding(finding_id: UUID, request: Request) -> FindingSummary | object:
    auth = request.state.auth
    settings = request.app.state.settings
    with tenant_transaction(settings.database_url, auth.tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.id, f.etag, f.control_id, fv.lifecycle_state, fv.outcome_state
            FROM finding f
            JOIN finding_version fv ON fv.finding_id = f.id
              AND fv.version_number = f.current_version_number
            WHERE f.tenant_id = %s AND f.id = %s
            """,
            (auth.tenant_id, finding_id),
        )
        row = cur.fetchone()
    if row is None:
        return problem_response(status=404, title="Not found", detail="Finding not found")
    return FindingSummary(
        id=row[0],
        etag=str(row[1]),
        control_id=str(row[2]),
        lifecycle_state=str(row[3]),
        outcome_state=str(row[4]),
    )


@router.post("/{finding_id}/actions", response_model=ReviewActionResponse)
async def review_action(
    finding_id: UUID,
    request: Request,
    body: ReviewActionRequest,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> ReviewActionResponse | object:
    auth = request.state.auth
    settings = request.app.state.settings
    reviewer = get_reviewer(request)
    ledger = get_audit_ledger(request)
    actor = auth.actor_id

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
            etag, after = reviewer.apply_action(
                conn,
                tenant_id=auth.tenant_id,
                finding_id=finding_id,
                if_match=if_match,
                action=ReviewAction(body.action),
                actor_principal_id=actor,
                rationale_en=body.rationale_en,
                rationale_fr=body.rationale_fr,
                reason_code=body.reason_code,
                modified_outcome=body.modified_outcome,
                audit_append=audit_append,
            )
    except StaleFindingError:
        return problem_response(
            status=409,
            title="Conflict",
            detail="Finding was updated by another reviewer",
            type_uri="https://cleartrace.local/problems/stale-finding",
        )
    except SeparationOfDutiesError:
        return problem_response(
            status=403,
            title="Forbidden",
            detail="System owners cannot validate or modify their own findings",
        )
    except ValueError as exc:
        return problem_response(status=400, title="Invalid action", detail=str(exc))
    except LookupError:
        return problem_response(status=404, title="Not found", detail="Finding not found")

    return ReviewActionResponse(
        finding_id=finding_id,
        etag=etag,
        lifecycle_state=after.lifecycle_state,
        outcome_state=after.outcome_state,
    )
