from __future__ import annotations

from typing import Annotated
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from uuid6 import uuid7

from cleartrace_core_api.deps import get_audit_ledger, get_evidence_store
from cleartrace_core_api.errors import problem_response

router = APIRouter(prefix="/evidence", tags=["evidence"])

# Upper bound on one evidence upload (ASVS V12.1.1); larger files get 413.
MAX_EVIDENCE_BYTES = 25 * 1024 * 1024


class EvidenceVersionResponse(BaseModel):
    id: UUID
    artefact_id: UUID
    sha256: str
    authorized_submitter: bool
    quarantined: bool
    submitter_role_at_time: str


class UploadEvidenceForm(BaseModel):
    artefact_class: str
    title_en: str = Field(default="Evidence artefact")
    title_fr: str = Field(default="Artefact de preuve")
    media_type: str = "application/octet-stream"


@router.post("", status_code=201, response_model=EvidenceVersionResponse)
async def upload_evidence(
    request: Request,
    file: Annotated[UploadFile, File()],
    artefact_class: Annotated[str, Form()],
    title_en: Annotated[str, Form()] = "Evidence artefact",
    title_fr: Annotated[str, Form()] = "Artefact de preuve",
) -> EvidenceVersionResponse | object:
    auth = request.state.auth
    settings = request.app.state.settings
    evidence_store = get_evidence_store(request)
    ledger = get_audit_ledger(request)
    payload = await file.read(MAX_EVIDENCE_BYTES + 1)
    if len(payload) > MAX_EVIDENCE_BYTES:
        return problem_response(
            status=413,
            title="Payload too large",
            detail=f"Evidence files are limited to {MAX_EVIDENCE_BYTES} bytes",
        )
    # actor_id never raises on a malformed principal claim, so a bad header is not a 500.
    principal_id = auth.actor_id if auth.raw_claims.get("principal_id") else uuid7()
    metadata = {
        "artefact_class": artefact_class,
        "title_en": title_en,
        "title_fr": title_fr,
        "media_type": file.content_type or "application/octet-stream",
    }

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
            version_id = evidence_store.store_artefact_tx(
                conn,
                tenant_id=auth.tenant_id,
                principal_id=principal_id,
                payload=payload,
                metadata=dict(metadata),
                audit_append=audit_append,
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT evidence_artefact_id, sha256, authorized_submitter, quarantined,
                           submitter_role_at_time
                    FROM evidence_version WHERE id = %s
                    """,
                    (version_id,),
                )
                row = cur.fetchone()
    except ValueError as exc:
        return problem_response(status=400, title="Invalid evidence", detail=str(exc))

    if row is None:
        return problem_response(
            status=500, title="Storage error", detail="Evidence missing after upload"
        )
    artefact_id, sha256, authorized, quarantined, role_at = row
    return EvidenceVersionResponse(
        id=version_id,
        artefact_id=artefact_id,
        sha256=str(sha256),
        authorized_submitter=bool(authorized),
        quarantined=bool(quarantined),
        submitter_role_at_time=str(role_at),
    )
