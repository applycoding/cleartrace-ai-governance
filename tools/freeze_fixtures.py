#!/usr/bin/env python3
"""Download and freeze public test fixtures (blueprint section 20)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST_PATH = FIXTURES / "manifest.json"
CHECKSUMS_PATH = FIXTURES / "checksums.sha256"
LICENSES_PATH = FIXTURES / "LICENSES.md"

TABLE_HEADER = (
    "| File | Source | Licence | Attribution | SHA-256 |",
    "| --- | --- | --- | --- | --- |",
)


@dataclass(frozen=True)
class FixtureSpec:
    rel_path: str
    url: str
    licence: str
    attribution: str
    optional: bool = False


SPECS: list[FixtureSpec] = [
    FixtureSpec(
        "gc-ai-register/gc-ai-register-mvp-registre-de-lia-du-gc-pmv-04-26.csv",
        "https://open.canada.ca/data/dataset/"
        "gc-ai-register-mvp-registre-de-lia-du-gc-pmv/resource/"
        "download/gc-ai-register-mvp-registre-de-lia-du-gc-pmv-04-26.csv",
        "Open Government Licence – Canada",
        "Government of Canada GC AI Register (open.canada.ca)",
    ),
    FixtureSpec(
        "aia/survey-enfr.json",
        "https://raw.githubusercontent.com/canada-ca/aia-eia-js/main/survey-enfr.json",
        "MIT",
        "canada-ca/aia-eia-js (pin commit in manifest.json at freeze time)",
    ),
    FixtureSpec(
        "aia/departments.json",
        "https://raw.githubusercontent.com/canada-ca/aia-eia-js/main/departments.json",
        "MIT",
        "canada-ca/aia-eia-js",
    ),
    FixtureSpec(
        "aia-results/ircc-aast.json",
        "https://open.canada.ca/data/dataset/"
        "algorithmic-impact-assessment-aia-results-resultats-de-leia/resource/"
        "download/aia-results-resultats-de-leia-1.json",
        "Open Government Licence – Canada",
        "IRCC AAST published AIA results",
        optional=True,
    ),
    FixtureSpec(
        "termium/termium-sample.xml",
        "https://open.canada.ca/data/dataset/terminology-plus-termium-plus/resource/"
        "download/termiumplus_open_data.zip",
        "Open Government Licence – Canada",
        "TERMIUM Plus open data (sample extracted locally when zip fetched)",
        optional=True,
    ),
    FixtureSpec(
        "synthetic/marked-synthetic-patients.json",
        "",
        "Apache-2.0 (generated synthetic data)",
        "ClearTrace synthetic Synthea-style patient records for tests",
    ),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_synthetic(path: Path) -> None:
    payload = {
        "synthetic": True,
        "description_en": "Synthetic patient-like records for ClearTrace tests",
        "description_fr": "Dossiers synthétiques de type patient pour les tests ClearTrace",
        "records": [{"id": "syn-1", "postal_code": "K1A0A6"}],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def _parse_existing_licence_rows(text: str) -> dict[str, str]:
    """Return rel_path -> full table row for paths managed by this tool."""
    rows: dict[str, str] = {}
    in_table = False
    for line in text.splitlines():
        if line.strip() == TABLE_HEADER[0]:
            in_table = True
            continue
        if in_table and line.startswith("| `"):
            match = re.match(r"\| `([^`]+)` \|", line)
            if match:
                rel = match.group(1)
                managed = any(spec.rel_path == rel for spec in SPECS)
                if managed:
                    rows[rel] = line
        if in_table and line.startswith("Run `uv run python tools/freeze_fixtures.py`"):
            break
    return rows


def _merge_licence_markdown(
    existing: str,
    managed_rows: dict[str, str],
    new_rows: dict[str, str],
) -> str:
    merged = dict(managed_rows)
    merged.update(new_rows)
    if not existing.strip():
        lines = [
            "# Fixtures licence register (step 4)",
            "",
            "Public datasets used in tests with source URL, licence, and attribution.",
            "",
            *TABLE_HEADER,
        ]
        for spec in SPECS:
            row = merged.get(spec.rel_path)
            if row:
                lines.append(row)
        lines.extend(
            [
                "",
                "Run `uv run python tools/freeze_fixtures.py` before G0 to refresh managed rows.",
                "",
            ]
        )
        return "\n".join(lines)

    before, _, after = existing.partition(TABLE_HEADER[0])
    if not _:
        return existing

    table_and_rest = after
    footer_idx = table_and_rest.find("Run `uv run python tools/freeze_fixtures.py`")
    if footer_idx == -1:
        footer = (
            "\nRun `uv run python tools/freeze_fixtures.py` before G0 to refresh managed rows.\n"
        )
        tail = ""
    else:
        footer = table_and_rest[footer_idx:]
        tail = table_and_rest[footer_idx + len(footer) :]

    lines = [before.rstrip(), "", TABLE_HEADER[0], TABLE_HEADER[1]]
    seen: set[str] = set()
    for line in table_and_rest.splitlines():
        if line.startswith("| `"):
            match = re.match(r"\| `([^`]+)` \|", line)
            if match:
                rel = match.group(1)
                if rel in merged:
                    lines.append(merged[rel])
                    seen.add(rel)
                else:
                    lines.append(line)
        elif line == TABLE_HEADER[1]:
            continue
        elif line.startswith("Run `uv run python tools/freeze_fixtures.py`"):
            break

    for spec in SPECS:
        if spec.rel_path not in seen and spec.rel_path in merged:
            lines.append(merged[spec.rel_path])

    lines.append("")
    lines.append(footer.strip())
    if tail.strip():
        lines.append(tail.strip())
    return "\n".join(lines) + "\n"


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    existing_licences = (
        LICENSES_PATH.read_text(encoding="utf-8") if LICENSES_PATH.exists() else ""
    )
    existing_managed = _parse_existing_licence_rows(existing_licences)

    manifest: dict[str, object] = {"frozen_at": None, "files": []}
    new_rows: dict[str, str] = {}
    checksum_lines: list[str] = []

    for spec in SPECS:
        target = FIXTURES / spec.rel_path
        if not spec.url:
            if not target.exists():
                _write_synthetic(target)
        else:
            try:
                _download(spec.url, target)
            except OSError as exc:
                if spec.optional:
                    print(f"skip optional {spec.rel_path}: {exc}")
                    continue
                raise
        digest = _sha256(target)
        checksum_lines.append(f"{digest}  {spec.rel_path}")
        url = spec.url or "generated"
        new_rows[spec.rel_path] = (
            f"| `{spec.rel_path}` | {url} | {spec.licence} | {spec.attribution} | `{digest}` |"
        )
        manifest["files"].append(
            {"path": spec.rel_path, "sha256": digest, "licence": spec.licence, "url": spec.url}
        )

    from datetime import UTC, datetime

    manifest["frozen_at"] = datetime.now(tz=UTC).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    CHECKSUMS_PATH.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    LICENSES_PATH.write_text(
        _merge_licence_markdown(existing_licences, existing_managed, new_rows),
        encoding="utf-8",
    )
    print(f"frozen {len(checksum_lines)} fixture files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
