"""User-facing report and export strings (EN/FR)."""

from __future__ import annotations

from dataclasses import dataclass

from cleartrace_reports.models import ReportType

NA_NOTE_EN = "Pass rates exclude N/A outcomes (lossy-for-state-only-consumers)."
NA_NOTE_FR = (
    "Les taux de réussite excluent les résultats N/A (perte pour les consommateurs d'état seul)."
)

HTML_TABLE_HEADER_EN = ("Section", "Value")
HTML_TABLE_HEADER_FR = ("Section", "Valeur")

CSV_HEADER_EN = "metric,value"
CSV_HEADER_FR = "indicateur,valeur"


@dataclass(frozen=True)
class ReportCopy:
    title_en: str
    title_fr: str
    sections_en: list[tuple[str, str]]
    sections_fr: list[tuple[str, str]]


REPORT_COPY: dict[ReportType, ReportCopy] = {
    ReportType.PORTFOLIO_STATUS: ReportCopy(
        title_en="Portfolio status",
        title_fr="État du portefeuille",
        sections_en=[
            ("Active systems", "12"),
            ("Open non-conformities", "3"),
        ],
        sections_fr=[
            ("Systèmes actifs", "12"),
            ("Non-conformités ouvertes", "3"),
        ],
    ),
    ReportType.SYSTEM_DOSSIER: ReportCopy(
        title_en="Compliance dossier",
        title_fr="Dossier de conformité",
        sections_en=[
            ("System", "SYS-01"),
            ("Frameworks applied", "DADM, AIA"),
        ],
        sections_fr=[
            ("Système", "SYS-01"),
            ("Cadres appliqués", "DADM, AIA"),
        ],
    ),
    ReportType.FRAMEWORK_COVERAGE: ReportCopy(
        title_en="Framework coverage",
        title_fr="Couverture des cadres",
        sections_en=[("Controls assessed", "42"), ("Coverage ratio", "0.91")],
        sections_fr=[("Contrôles évalués", "42"), ("Ratio de couverture", "0,91")],
    ),
    ReportType.POLICY_IMPACT: ReportCopy(
        title_en="Policy impact summary",
        title_fr="Sommaire d'impact des politiques",
        sections_en=[("Impacted controls", "7"), ("Systems flagged", "4")],
        sections_fr=[("Contrôles touchés", "7"), ("Systèmes signalés", "4")],
    ),
    ReportType.AIA_SUMMARY: ReportCopy(
        title_en="AIA summary",
        title_fr="Sommaire EIA",
        sections_en=[("Overall level", "Moderate"), ("Open mitigations", "2")],
        sections_fr=[("Niveau global", "Modéré"), ("Atténuations ouvertes", "2")],
    ),
    ReportType.AUDIT_EXTRACT: ReportCopy(
        title_en="Audit extract",
        title_fr="Extrait de vérification",
        sections_en=[("Events exported", "250"), ("Checkpoint", "latest")],
        sections_fr=[("Événements exportés", "250"), ("Point de contrôle", "dernier")],
    ),
}


def report_template_rows() -> list[tuple[str, str, str]]:
    """Return (template_id, text_en, text_fr) for each report/export string block."""
    rows: list[tuple[str, str, str]] = [
        ("report:na_note", NA_NOTE_EN, NA_NOTE_FR),
        (
            "report:html_table_header",
            " / ".join(HTML_TABLE_HEADER_EN),
            " / ".join(HTML_TABLE_HEADER_FR),
        ),
        ("report:csv_header", CSV_HEADER_EN, CSV_HEADER_FR),
    ]
    for report_type, copy in REPORT_COPY.items():
        rid = report_type.value
        rows.append((f"report:{rid}:title", copy.title_en, copy.title_fr))
        for idx, (label_en, value_en) in enumerate(copy.sections_en):
            label_fr, value_fr = copy.sections_fr[idx]
            rows.append(
                (
                    f"report:{rid}:section_{idx + 1}",
                    f"{label_en}: {value_en}",
                    f"{label_fr}: {value_fr}",
                )
            )
    return rows
