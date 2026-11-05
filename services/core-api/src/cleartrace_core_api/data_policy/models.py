from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from cleartrace_core_api.strict import StrictModel


class DeletionCertificateStatus(StrEnum):
    PENDING = "pending"
    FINAL = "final"


class RetentionRuleBody(StrictModel):
    artefact_class: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    configured_retention_days: int = Field(ge=1, le=36_500)
    statutory_floor_days: int = Field(default=730, ge=0, le=36_500)

    @field_validator("configured_retention_days", "statutory_floor_days", mode="before")
    @classmethod
    def _reject_bool(cls, value: object) -> object:
        # JSON true/false is not a day count; pydantic's lax mode would coerce it.
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value


class TenantDataPolicyView(BaseModel):
    tenant_id: UUID
    residency_cell_id: UUID | None
    classification_ceiling: str
    security_profile: str
    retention_rules: list[RetentionRuleBody]


class LegalHoldCreate(StrictModel):
    scope: dict[str, object]
    reason_en: str = Field(min_length=1, max_length=2000)
    reason_fr: str = Field(min_length=1, max_length=2000)


class LegalHoldView(BaseModel):
    id: UUID
    scope: dict[str, object]
    reason_en: str
    reason_fr: str
    active: bool
    created_at: datetime


class DeletionRequestCreate(StrictModel):
    payload_ids: list[UUID] = Field(min_length=1)


class DeletionRequestView(BaseModel):
    id: UUID
    payload_ids: list[UUID]
    status: str
    certificate_id: UUID | None = None
    requested_at: datetime
    completed_at: datetime | None = None


class DeletionCertificateView(BaseModel):
    id: UUID
    deletion_request_id: UUID
    status: DeletionCertificateStatus
    key_destruction_scheduled_at: datetime | None
    key_destroyed_at: datetime | None
    backup_expiry_note_en: str
    backup_expiry_note_fr: str
    issued_at: datetime
    finalized_at: datetime | None = None


class BackupSnapshotView(BaseModel):
    id: UUID
    snapshot_label: str
    manifest_sha256: str
    payload_count: int
    created_at: datetime
