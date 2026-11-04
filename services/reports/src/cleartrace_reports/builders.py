from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cleartrace_reports.user_strings import NA_NOTE_EN, NA_NOTE_FR


def _env() -> Environment:
    templates = Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(templates)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html(
    *,
    language: str,
    title: str,
    as_of: str,
    framework_versions: list[str],
    sections: list[tuple[str, str]],
) -> str:
    env = _env()
    template = env.get_template("report.html.j2")
    note = NA_NOTE_FR if language.startswith("fr") else NA_NOTE_EN
    return template.render(
        language=language,
        title=title,
        as_of=as_of,
        framework_versions=framework_versions,
        sections=sections,
        na_note=note,
    )


def render_csv(
    *,
    language: str,
    rows: list[dict[str, str]],
) -> str:
    if not rows:
        header = "metric,value" if not language.startswith("fr") else "indicateur,valeur"
        return f"{header}\n"
    keys = list(rows[0].keys())
    lines = [",".join(keys)]
    for row in rows:
        lines.append(",".join(row[k] for k in keys))
    return "\n".join(lines) + "\n"


def html_to_pdf(html: str) -> bytes:
    from io import BytesIO

    from xhtml2pdf import pisa

    output = BytesIO()
    pisa.CreatePDF(html, dest=output, encoding="utf-8")
    return output.getvalue()
