from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OutcomeState(StrEnum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    NOT_APPLICABLE = "not_applicable"
    UNABLE_TO_DETERMINE = "unable_to_determine"


class BilingualText(BaseModel):
    en: str = Field(..., alias="en")
    fr: str = Field(..., alias="fr")

    model_config = {"populate_by_name": True}


class TenantRef(BaseModel):
    id: UUID
    slug: str


class CellRef(BaseModel):
    id: UUID
    slug: str


class ProblemDetail(BaseModel):
    """RFC 9457 problem details."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class IdempotencyContext(BaseModel):
    key: str
    request_hash: str
    created_at: datetime
