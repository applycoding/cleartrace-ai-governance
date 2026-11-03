from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class ReportType(StrEnum):
    SYSTEM_DOSSIER = "system_compliance_dossier"
    PORTFOLIO_STATUS = "portfolio_status"
    FRAMEWORK_COVERAGE = "framework_coverage"
    POLICY_IMPACT = "policy_impact"
    AIA_SUMMARY = "aia_summary"
    AUDIT_EXTRACT = "audit_extract"


class ReportFormat(StrEnum):
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"


@dataclass(slots=True)
class ReportSpec:
    tenant_id: UUID
    report_type: ReportType | str
    language: str
    format: ReportFormat | str
    scope: dict[str, Any]
    as_of: datetime | None = None


@dataclass(slots=True)
class ReportArtefact:
    report_id: UUID
    content_type: str
    filename: str
    body: bytes
    language: str
    as_of: datetime
    na_excluded_note_en: str
    na_excluded_note_fr: str
