#!/usr/bin/env python3
"""Licence gate: apply docs/LICENSE_POLICY.md to every shipped dependency.

Policy (explicit, no blanket ignore):
  * ClearTrace's own manifests must carry the ClearTrace licence (LicenseRef / UNLICENSED).
  * Third-party permissive licences are allowed.
  * LGPL and MPL are allowed only when the package is listed in the "used unmodified"
    table of THIRD_PARTY_LICENSES.md, and that file must be current.
  * Strong copyleft (GPL, AGPL), source-available (SSPL, BUSL/BSL, Elastic) and
    unknown licences fail the gate in our own dependencies.
  * Container base-image OS packages are reported (tools/image_licence_report.py), not gated.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import third_party_licences as tpl  # noqa: E402

OWN_LICENCE = "LicenseRef-ClearTrace-Evaluation-Only"

# Licence families the blueprint disallows inside shipped images (§13 line 716). The
# image report (tools/image_licence_report.py) uses this list to report OS packages.
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

# Classes the policy rejects in our own dependencies.
REJECTED_CLASSES = ("strong-copyleft", "source-available", "unknown")
# Strong-copyleft and source-available tokens that must not appear in our own source paths.
OWN_SOURCE_FORBIDDEN = re.compile(r"\b(?:A?GPL(?:-?[23])?|SSPL|BUSL|Elastic License)\b")

TARGETS = [
    ROOT / "pyproject.toml",
    ROOT / "packages",
    ROOT / "services",
    ROOT / "db",
    ROOT / "web" / "package.json",
]
SBOM_PATH = ROOT / "sbom.json"
THIRD_PARTY = ROOT / "THIRD_PARTY_LICENSES.md"


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [
        f"{path}: contains strong-copyleft or source-available licence token {m.group(0)}"
        for m in OWN_SOURCE_FORBIDDEN.finditer(text)
    ]


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


def own_manifests() -> list[str]:
    problems: list[str] = []
    for path in [
        ROOT / "pyproject.toml",
        *sorted(ROOT.glob("packages/*/pyproject.toml")),
        *sorted(ROOT.glob("services/*/pyproject.toml")),
        ROOT / "db" / "pyproject.toml",
    ]:
        if not path.is_file():
            continue
        lic = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {}).get("license")
        text = lic.get("text") if isinstance(lic, dict) else lic
        if text != OWN_LICENCE:
            problems.append(
                f"{path.relative_to(ROOT)}: project licence is {lic!r}, expected {OWN_LICENCE}"
            )
    pkg = json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    if pkg.get("license") != "UNLICENSED" or pkg.get("private") is not True:
        problems.append('web/package.json: expected "license": "UNLICENSED" and "private": true')
    return problems


def _unmodified_table() -> set[tuple[str, str]]:
    if not THIRD_PARTY.is_file():
        return set()
    text = THIRD_PARTY.read_text(encoding="utf-8")
    section = text.split("## LGPL and MPL components (used unmodified)", 1)[-1].split("\n## ", 1)[0]
    rows: set[tuple[str, str]] = set()
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[4] == "unmodified":
            rows.add((cells[0], cells[1]))
    return rows


def dependency_policy(deps: list[tpl.Dep]) -> list[str]:
    problems: list[str] = []
    listed = _unmodified_table()
    for d in deps:
        cls = tpl.classify(d.licence)
        if cls in REJECTED_CLASSES:
            problems.append(
                f"{d.ecosystem} {d.name} {d.version}: licence {d.licence!r} is {cls}; not allowed"
            )
        elif cls == "weak-copyleft" and (d.ecosystem, d.name) not in listed:
            problems.append(
                f"{d.ecosystem} {d.name} {d.version}: {d.licence} not listed as used unmodified in THIRD_PARTY_LICENSES.md"
            )
    return problems


def scan_sbom(path: Path) -> list[str]:
    """Apply the dependency policy to licences recorded on shipped SBOM components."""
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for component in doc.get("components", []) or []:
        if not isinstance(component, dict) or component.get("scope") == "excluded":
            continue
        for token in licence_tokens(component):
            if token == OWN_LICENCE:
                continue
            cls = tpl.classify(token)
            if cls in ("strong-copyleft", "source-available"):
                name = str(component.get("name", "unknown"))
                problems.append(f"sbom component {name}: licence {token!r} is {cls}")
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
    problems.extend(own_manifests())
    deps = tpl.collect()
    problems.extend(dependency_policy(deps))
    current = THIRD_PARTY.read_text(encoding="utf-8") if THIRD_PARTY.is_file() else ""
    if current != tpl.render(deps):
        problems.append(
            "THIRD_PARTY_LICENSES.md is out of date; run uv run python tools/third_party_licences.py"
        )
    problems.extend(scan_sbom(SBOM_PATH))
    if problems:
        print("\n".join(problems))
        return 1
    weak = sorted(f"{d.name}" for d in deps if tpl.classify(d.licence) == "weak-copyleft")
    print(
        f"licence gate: OK ({len(deps)} shipped dependencies checked against docs/LICENSE_POLICY.md; "
        f"{len(weak)} LGPL/MPL used unmodified and listed in THIRD_PARTY_LICENSES.md; "
        "0 strong-copyleft, source-available or unknown; base-image OS packages reported, not gated)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
