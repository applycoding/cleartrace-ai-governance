from __future__ import annotations

from uuid import UUID

import pytest
from cleartrace_reports.models import ReportFormat, ReportType
from cleartrace_reports.service import ReportService

TENANT = UUID("11111111-1111-7111-8111-111111111101")


@pytest.mark.asyncio
async def test_html_report_en() -> None:
    svc = ReportService()
    artefact = svc.build_sync(
        TENANT,
        {
            "type": ReportType.SYSTEM_DOSSIER,
            "language": "en-CA",
            "format": ReportFormat.HTML,
            "scope": {"system_id": "SYS-01"},
        },
    )
    assert artefact.content_type.startswith("text/html")
    body = artefact.body.decode("utf-8")
    assert "Compliance dossier" in body
    assert "N/A" in body


@pytest.mark.asyncio
async def test_pdf_report_fr() -> None:
    svc = ReportService()
    artefact = svc.build_sync(
        TENANT,
        {
            "type": ReportType.PORTFOLIO_STATUS,
            "language": "fr-CA",
            "format": ReportFormat.PDF,
            "scope": {},
        },
    )
    assert artefact.body.startswith(b"%PDF")
    assert artefact.language.startswith("fr")


def test_csv_report_en() -> None:
    svc = ReportService()
    artefact = svc.build_sync(
        TENANT,
        {
            "type": ReportType.AUDIT_EXTRACT,
            "language": "en-CA",
            "format": ReportFormat.CSV,
            "scope": {},
        },
    )
    text = artefact.body.decode("utf-8")
    assert text.splitlines()[0] == "metric,value"


def test_unknown_report_type_falls_back_to_dossier() -> None:
    """The API default type "system_dossier" is not a ReportType member; it must render."""
    artefact = ReportService().build_sync(
        TENANT,
        {"type": "system_dossier", "language": "en-CA", "format": ReportFormat.HTML, "scope": {}},
    )
    assert "Compliance dossier" in artefact.body.decode("utf-8")
