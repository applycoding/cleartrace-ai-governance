#!/usr/bin/env python3
"""Fail the build if shipped dependency licences are not permissive."""

from __future__ import annotations

import json
from pathlib import Path

DISALLOWED = (
    "AGPL",
    "GPL",
    "LGPL",
    "SSPL",
    "BSL",
    "ELASTIC",
    "Elastic License",
    "MPL-2.0",
    "BUSL",
)

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "pyproject.toml",
    ROOT / "packages",
    ROOT / "services",
    ROOT / "db",
    ROOT / "web" / "package.json",
]
SBOM_PATH = ROOT / "sbom.json"


def scan_file(path: Path) -> list[str]:
    hits: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for token in DISALLOWED:
        if token in text:
            hits.append(f"{path}: contains disallowed licence token {token}")
    return hits


def licence_tokens(component: dict[str, object]) -> list[str]:
    """Licence ids, names and SPDX expressions recorded on a CycloneDX component."""
    tokens: list[str] = []
    for entry in component.get("licenses", []) or []:  # type: ignore[union-attr]
        if not isinstance(entry, dict):
            continue
        lic = entry.get("license")
        if isinstance(lic, dict):
            for key in ("id", "name"):
                if lic.get(key):
                    tokens.append(str(lic[key]))
        elif isinstance(lic, str):
            tokens.append(lic)
        if entry.get("expression"):
            tokens.append(str(entry["expression"]))
    for prop in component.get("properties", []) or []:  # type: ignore[union-attr]
        if isinstance(prop, dict) and prop.get("name") == "cleartrace:licence":
            tokens.append(str(prop.get("value", "")))
    return [t for t in tokens if t]


def scan_sbom(path: Path) -> list[str]:
    """Fail on any component in the repository SBOM that records a disallowed licence."""
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for component in doc.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        hits = [t for t in licence_tokens(component) if any(b.upper() in t.upper() for b in DISALLOWED)]
        if hits:
            name = str(component.get("name", "unknown"))
            problems.append(f"sbom component {name}: disallowed licence {'; '.join(hits)!r}")
    return problems


def main() -> int:
    problems: list[str] = []
    for target in TARGETS:
        if target.is_file():
            problems.extend(scan_file(target))
        elif target.is_dir():
            for file in target.rglob("*"):
                if file.suffix in {".toml", ".py", ".json", ".md", ".yaml", ".yml"}:
                    problems.extend(scan_file(file))
    problems.extend(scan_sbom(SBOM_PATH))
    if problems:
        print("\n".join(problems))
        return 1
    print("licence gate: OK (no disallowed token in shipped source paths; no disallowed licence recorded in sbom.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
