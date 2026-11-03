from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.trl5

ROOT = Path(__file__).resolve().parents[2]


def test_t28_full_inventory_sbom_and_licence_gate() -> None:
    subprocess.run(["uv", "run", "python", "tools/sbom_builder.py"], cwd=ROOT, check=True)
    sbom_path = ROOT / "sbom.json"
    doc = json.loads(sbom_path.read_text(encoding="utf-8"))
    components = doc.get("components", [])
    assert len(components) >= 5
    types = {c.get("type") for c in components}
    assert "application" in types
    assert "library" in types
    assert "data" in types or any(c.get("type") == "container" for c in components)
    containers = [c for c in components if c.get("type") == "container"]
    assert len(containers) >= 3, "shipped Compose images must appear in the SBOM"
    compose = (ROOT / "deploy" / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
    for line in compose.splitlines():
        if "image:" in line:
            ref = line.split("image:", maxsplit=1)[1].strip()
            assert any(ref in str(c.get("name", "")) or ref in str(c.get("properties", "")) for c in containers), (
                f"missing container SBOM entry for {ref}"
            )

    gate = subprocess.run(["uv", "run", "python", "tools/licence_gate.py"], cwd=ROOT)
    assert gate.returncode == 0, "licence gate must report 0 disallowed licences"

    disallowed = ("AGPL", "GPL", "LGPL", "SSPL", "BSL", "Elastic License", "MPL-2.0")
    blob = sbom_path.read_text(encoding="utf-8")
    for token in disallowed:
        assert token not in blob
