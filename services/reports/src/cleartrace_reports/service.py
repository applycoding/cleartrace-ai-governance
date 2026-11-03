from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from uuid6 import uuid7

from cleartrace_reports.builders import NA_NOTE_EN, NA_NOTE_FR, html_to_pdf, render_csv, render_html
from cleartrace_reports.models import ReportArtefact, ReportFormat, ReportSpec, ReportType


class ReportService:
    """Implements the cleartrace_contracts ReportBuilder protocol."""

    async def build_report(self, tenant_id: UUID, spec: dict[str, object]) -> UUID:
        artefact = self.build_sync(tenant_id, spec)
        return artefact.report_id

    def build_sync(self, tenant_id: UUID, spec: dict[str, object]) -> ReportArtefact:
        parsed = _parse_spec(tenant_id, spec)
        as_of = parsed.as_of or datetime.now(UTC)
        title, sections, rows = _sample_content(parsed)
        language = parsed.language
        fmt = ReportFormat(str(parsed.format))

        if fmt == ReportFormat.HTML:
            body = render_html(
                language=language,
                title=title,
                as_of=as_of.isoformat(),
                framework_versions=["DADM 2024.1", "AIA 2024.1"],
                sections=sections,
            ).encode("utf-8")
            content_type = "text/html; charset=utf-8"
            filename = f"report-{parsed.report_type}.html"
        elif fmt == ReportFormat.PDF:
            html = render_html(
                language=language,
                title=title,
                as_of=as_of.isoformat(),
                framework_versions=["DADM 2024.1", "AIA 2024.1"],
                sections=sections,
            )
            body = html_to_pdf(html)
            content_type = "application/pdf"
            filename = f"report-{parsed.report_type}.pdf"
        else:
            body = render_csv(language=language, rows=rows).encode("utf-8")
            content_type = "text/csv; charset=utf-8"
            filename = f"report-{parsed.report_type}.csv"

        return ReportArtefact(
            report_id=uuid7(),
            content_type=content_type,
            filename=filename,
            body=body,
            language=language,
            as_of=as_of,
            na_excluded_note_en=NA_NOTE_EN,
            na_excluded_note_fr=NA_NOTE_FR,
        )


def _parse_spec(tenant_id: UUID, spec: dict[str, object]) -> ReportSpec:
    return ReportSpec(
        tenant_id=tenant_id,
        report_type=str(spec.get("type", ReportType.SYSTEM_DOSSIER)),
        language=str(spec.get("language", "en-CA")),
        format=str(spec.get("format", ReportFormat.HTML)),
        scope=_coerce_dict(spec.get("scope")),
        as_of=_coerce_datetime(spec.get("as_of")),
    )


def _sample_content(
    spec: ReportSpec,
) -> tuple[str, list[tuple[str, str]], list[dict[str, str]]]:
    lang_fr = spec.language.startswith("fr")
    if spec.report_type == ReportType.PORTFOLIO_STATUS:
        title = "État du portefeuille" if lang_fr else "Portfolio status"
        sections = [
            (
                "Systèmes actifs" if lang_fr else "Active systems",
                "12" if not lang_fr else "12",
            ),
            (
                "Non-conformités ouvertes" if lang_fr else "Open non-conformities",
                "3",
            ),
        ]
        rows = [
            {"metric" if not lang_fr else "indicateur": "systems", "value": "12"},
            {"metric" if not lang_fr else "indicateur": "open_nc", "value": "3"},
        ]
        return title, sections, rows

    title = "Dossier de conformité" if lang_fr else "Compliance dossier"
    system_label = "Système" if lang_fr else "System"
    sections = [
        (system_label, str(spec.scope.get("system_id", "SYS-01"))),
        (
            "Cadres appliqués" if lang_fr else "Frameworks applied",
            "DADM, AIA",
        ),
    ]
    rows = [
        {"field": "system_id", "value": str(spec.scope.get("system_id", "SYS-01"))},
        {"field": "frameworks", "value": "DADM,AIA"},
    ]
    return title, sections, rows


def _coerce_dict(value: object | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _coerce_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
