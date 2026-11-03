from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from cleartrace_core_api.data_policy.models import (
    DeletionCertificateView,
    DeletionRequestCreate,
    DeletionRequestView,
    LegalHoldCreate,
    LegalHoldView,
    RetentionRuleBody,
    TenantDataPolicyView,
)
from cleartrace_core_api.data_policy.service import DataPolicyService
from cleartrace_core_api.errors import problem_response

router = APIRouter(prefix="/data-policy", tags=["data-policy"])


class RetentionUpdateBody(BaseModel):
    rules: list[RetentionRuleBody]


def _service(request: Request) -> DataPolicyService:
    settings = request.app.state.settings
    return DataPolicyService(settings.database_url.replace("+psycopg", ""))


@router.get("", response_model=TenantDataPolicyView)
async def get_data_policy(request: Request) -> TenantDataPolicyView:
    auth = request.state.auth
    return _service(request).get_policy(auth.tenant_id)


@router.put("/retention", response_model=TenantDataPolicyView)
async def put_retention(
    request: Request, body: RetentionUpdateBody
) -> TenantDataPolicyView | Response:
    auth = request.state.auth
    return _service(request).upsert_retention(auth.tenant_id, body.rules)


@router.post("/legal-holds", status_code=201, response_model=LegalHoldView)
async def post_legal_hold(request: Request, body: LegalHoldCreate) -> LegalHoldView | Response:
    auth = request.state.auth
    return _service(request).create_legal_hold(
        auth.tenant_id,
        scope=body.scope,
        reason_en=body.reason_en,
        reason_fr=body.reason_fr,
    )


@router.post("/deletion-requests", status_code=201, response_model=DeletionRequestView)
async def post_deletion_request(
    request: Request, body: DeletionRequestCreate
) -> DeletionRequestView | Response:
    auth = request.state.auth
    try:
        return _service(request).request_deletion(auth.tenant_id, body.payload_ids)
    except ValueError as exc:
        return problem_response(
            status=409,
            title="Deletion blocked",
            detail=str(exc),
            type_uri="https://cleartrace.local/problems/deletion-blocked",
        )


@router.get("/deletion-certificates/{certificate_id}", response_model=DeletionCertificateView)
async def get_deletion_certificate(
    request: Request, certificate_id: UUID
) -> DeletionCertificateView | Response:
    auth = request.state.auth
    cert = _service(request).get_certificate(auth.tenant_id, certificate_id)
    if cert is None:
        return problem_response(status=404, title="Not found", detail="Certificate not found")
    return cert
