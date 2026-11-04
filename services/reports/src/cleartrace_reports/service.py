from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from uuid6 import uuid7

from cleartrace_reports.builders import html_to_pdf, render_csv, render_html
from cleartrace_reports.models import ReportArtefact, ReportFormat, ReportSpec, ReportType
from cleartrace_reports.user_strings import NA_NOTE_EN, NA_NOTE_FR, REPORT_COPY


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
    # Unknown types (e.g. the API default "system_dossier") keep the old
    # behaviour: render the compliance dossier instead of raising.
    try:
        report_type = ReportType(str(spec.report_type))
    except ValueError:
        report_type = ReportType.SYSTEM_DOSSIER
    copy = REPORT_COPY.get(report_type, REPORT_COPY[ReportType.SYSTEM_DOSSIER])
    title = copy.title_fr if lang_fr else copy.title_en
    sections = copy.sections_fr if lang_fr else copy.sections_en
    if lang_fr:
        rows = [
            {"indicateur": label.lower().replace(" ", "_"), "valeur": value}
            for label, value in sections
        ]
    else:
        rows = [{"metric": label.lower().replace(" ", "_"), "value": value} for label, value in sections]
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
