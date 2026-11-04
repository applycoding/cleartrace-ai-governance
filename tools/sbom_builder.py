#!/usr/bin/env python3
"""Build a full-inventory CycloneDX 1.6 SBOM for ClearTrace (T-28)."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sbom.json"
FIXTURE_MANIFEST = ROOT / "tests" / "fixtures" / "manifest.json"
sys.path.insert(0, str(ROOT / "tools"))

import third_party_licences as tpl  # noqa: E402


def _component(
    name: str,
    version: str,
    ctype: str,
    extra: dict[str, str] | None = None,
) -> dict[str, object]:
    comp: dict[str, object] = {
        "type": ctype,
        "name": name,
        "version": version,
        "purl": f"pkg:generic/cleartrace/{name}@{version}",
    }
    if extra:
        comp["properties"] = [{"name": k, "value": v} for k, v in extra.items()]
    return comp


OWN_LICENCE = "LicenseRef-ClearTrace-Evaluation-Only"


def _with_licence(comp: dict[str, object], licence: str, scope: str) -> dict[str, object]:
    if licence and licence not in {"NOT INSTALLED"} and not licence.startswith("UNKNOWN"):
        comp["licenses"] = [{"expression": licence}]
    props = list(comp.get("properties", []) or [])  # type: ignore[call-overload]
    props.append({"name": "cleartrace:licence", "value": licence})
    comp["properties"] = props
    comp["scope"] = scope
    return comp


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _python_packages() -> list[dict[str, object]]:
    """Every installed Python distribution; shipped ones (non-dev in uv.lock) are scope required."""
    try:
        proc = subprocess.run(
            ["uv", "pip", "freeze"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        shipped = {_norm(d.name): d for d in tpl.python_deps()}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [_component("cleartrace-workspace", "0.1.0", "library")]
    components: list[dict[str, object]] = []
    seen: set[str] = set()
    for line in proc.stdout.splitlines():
        if "==" not in line:
            continue
        name, version = line.split("==", maxsplit=1)
        key = _norm(name)
        seen.add(key)
        if key in shipped:
            licence, scope = shipped[key].licence, "required"
        else:
            try:
                licence, _ = tpl.python_licence(importlib.metadata.distribution(name))
            except importlib.metadata.PackageNotFoundError:
                licence = "UNKNOWN"
            scope = "excluded"
        components.append(_with_licence(_component(name, version, "library"), licence, scope))
    for key, dep in sorted(shipped.items()):
        if key not in seen:
            components.append(
                _with_licence(_component(dep.name, dep.version, "library"), dep.licence, "excluded")
            )
    return components


def _npm_packages() -> list[dict[str, object]]:
    """Non-dev packages of the web build from web/package-lock.json."""
    if not tpl.NPM_LOCK.exists():
        return []
    return [
        _with_licence(_component(f"npm:{d.name}", d.version, "library"), d.licence, "required")
        for d in tpl.npm_deps()
    ]


def _fixture_components() -> list[dict[str, object]]:
    if not FIXTURE_MANIFEST.exists():
        return []
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    items: list[dict[str, object]] = []
    for entry in manifest.get("files", []):
        rel = entry["path"]
        path = ROOT / "tests" / "fixtures" / rel
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        items.append(
            _component(
                rel,
                digest[:12],
                "data",
                {"cleartrace:sha256": digest, "cleartrace:licence": entry.get("licence", "")},
            )
        )
    return items


def _image_components() -> list[dict[str, object]]:
    compose = ROOT / "deploy" / "compose" / "docker-compose.yml"
    if not compose.exists():
        return []
    text = compose.read_text(encoding="utf-8")
    images: list[dict[str, object]] = []
    for line in text.splitlines():
        if "image:" in line:
            ref = line.split("image:", maxsplit=1)[1].strip()
            images.append(_component(ref, "pinned", "container", {"cleartrace:image": ref}))
    offline = ROOT / "deploy" / "offline-bundle" / "images.manifest.json"
    if offline.exists():
        data = json.loads(offline.read_text(encoding="utf-8"))
        for item in data.get("images", []):
            images.append(
                _component(
                    item["reference"],
                    item.get("digest", "unknown"),
                    "container",
                    {"cleartrace:digest": item.get("digest", "")},
                )
            )
    return images


def build_sbom() -> dict[str, object]:
    components = (
        [
            _with_licence(
                _component("cleartrace-platform", "0.1.0", "application"), OWN_LICENCE, "required"
            )
        ]
        + _python_packages()
        + _npm_packages()
        + _fixture_components()
        + _image_components()
    )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "cleartrace",
                "version": "0.1.0",
                "licenses": [{"license": {"id": OWN_LICENCE}}],
            },
            "properties": [
                {
                    "name": "cleartrace:inventory",
                    "value": "code,python-deps,npm-deps,fixtures,containers",
                },
            ],
        },
        "components": components,
    }


def main() -> None:
    doc = build_sbom()
    OUTPUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(doc.get('components', []))} components)")


if __name__ == "__main__":
    main()
