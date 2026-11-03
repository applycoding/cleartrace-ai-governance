#!/usr/bin/env python3
"""Download and freeze public test fixtures (blueprint section 20)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST_PATH = FIXTURES / "manifest.json"
CHECKSUMS_PATH = FIXTURES / "checksums.sha256"
LICENSES_PATH = FIXTURES / "LICENSES.md"


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


def _licence_rows(entries: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "# Fixtures licence register (step 4)",
        "",
        "Public datasets used in tests with source URL, licence, and attribution.",
        "",
        "| File | Source | Licence | Attribution | SHA-256 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rel, url, licence, attribution, digest in entries:
        lines.append(f"| `{rel}` | {url or 'generated'} | {licence} | {attribution} | `{digest}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"frozen_at": None, "files": []}
    licence_entries: list[tuple[str, str, str, str, str]] = []
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
        licence_entries.append((spec.rel_path, spec.url, spec.licence, spec.attribution, digest))
        manifest["files"].append(
            {"path": spec.rel_path, "sha256": digest, "licence": spec.licence, "url": spec.url}
        )

    from datetime import UTC, datetime

    manifest["frozen_at"] = datetime.now(tz=UTC).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    CHECKSUMS_PATH.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    LICENSES_PATH.write_text(_licence_rows(licence_entries), encoding="utf-8")
    print(f"frozen {len(checksum_lines)} fixture files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
