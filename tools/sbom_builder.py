#!/usr/bin/env python3
"""Build a full-inventory CycloneDX 1.6 SBOM for ClearTrace (T-28)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sbom.json"
FIXTURE_MANIFEST = ROOT / "tests" / "fixtures" / "manifest.json"


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


def _python_packages() -> list[dict[str, object]]:
    try:
        proc = subprocess.run(
            ["uv", "pip", "freeze"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [_component("cleartrace-workspace", "0.1.0", "library")]
    components: list[dict[str, object]] = []
    for line in proc.stdout.splitlines():
        if "==" not in line:
            continue
        name, version = line.split("==", maxsplit=1)
        components.append(_component(name, version, "library"))
    return components


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
        [_component("cleartrace-platform", "0.1.0", "application")]
        + _python_packages()
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
            },
            "properties": [
                {"name": "cleartrace:inventory", "value": "code,python-deps,fixtures,containers"},
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
