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


def _license_tokens(component: dict[str, object]) -> list[str]:
    tokens: list[str] = []
    for entry in component.get("licenses", []) or []:
        if not isinstance(entry, dict):
            continue
        lic = entry.get("license")
        if isinstance(lic, dict):
            if lic.get("id"):
                tokens.append(str(lic["id"]))
            if lic.get("name"):
                tokens.append(str(lic["name"]))
        elif isinstance(lic, str):
            tokens.append(lic)
    for prop in component.get("properties", []) or []:
        if isinstance(prop, dict) and prop.get("name") == "cleartrace:licence":
            tokens.append(str(prop.get("value", "")))
    return tokens


def scan_sbom(path: Path) -> list[str]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for component in doc.get("components", []) or []:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name", "unknown"))
        ctype = str(component.get("type", ""))
        for token in _license_tokens(component):
            upper = token.upper()
            if any(block in upper for block in DISALLOWED):
                problems.append(
                    f"sbom component {name} ({ctype}): disallowed licence {token!r}"
                )
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
    print("licence gate: OK (no disallowed tokens in scanned shipped paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
