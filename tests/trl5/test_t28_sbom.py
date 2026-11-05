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
            assert any(
                ref in str(c.get("name", "")) or ref in str(c.get("properties", ""))
                for c in containers
            ), f"missing container SBOM entry for {ref}"

    gate = subprocess.run(["uv", "run", "python", "tools/licence_gate.py"], cwd=ROOT)
    assert gate.returncode == 0, "licence gate must report 0 disallowed licences"

    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    from third_party_licences import classify

    app = [c for c in components if c.get("type") == "application"]
    assert app, "ClearTrace application component missing"
    assert {"expression": "LicenseRef-ClearTrace-Evaluation-Only"} in app[0].get("licenses", [])
    shipped = [c for c in components if c.get("type") == "library" and c.get("scope") == "required"]
    assert len(shipped) >= 100, "shipped Python and npm dependencies must be listed with licences"
    for comp in shipped:
        recorded = [
            e["expression"]
            for e in comp.get("licenses", [])
            if isinstance(e, dict) and "expression" in e
        ]
        assert recorded, f"no licence recorded for shipped component {comp.get('name')}"
        # docs/LICENSE_POLICY.md: permissive allowed; LGPL/MPL only when listed as used
        # unmodified in THIRD_PARTY_LICENSES.md (checked by the gate above); strong
        # copyleft, source-available and unknown licences are not allowed.
        assert classify(recorded[0]) in {"permissive", "weak-copyleft"}, (
            comp.get("name"),
            recorded,
        )


def test_t28_image_inventory_lists_every_shipped_image(
    record_property: pytest.RecordProperty,
) -> None:
    """Every shipped image is either scanned by Syft or listed as not scanned with a reason.

    OS-package GPL/LGPL findings are covered by
    docs/licence_exceptions/SHIPPED_IMAGE_OS_PACKAGES.md. The ClearTrace core-api
    image must appear in the inventory; T-28 stays partial until CI records it as
    scanned.
    """
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    from image_licence_report import build_report, shipped_images

    report = build_report()
    images = report["images"]
    exception = ROOT / "docs" / "licence_exceptions" / "SHIPPED_IMAGE_OS_PACKAGES.md"
    assert exception.is_file(), "approved OS-package exception file missing"
    assert report.get("exception_file"), "licence report must record the exception file"
    assert any(
        "cleartrace-core-api" in str(i["image"]) for i in images
    ), "ClearTrace core-api image missing from inventory"
    assert isinstance(images, list)
    assert sorted(str(i["image"]) for i in images) == shipped_images()
    for image in images:
        if image["status"] == "scanned":
            assert int(image["components"]) > 0, f"empty SBOM for {image['image']}"
        else:
            assert image.get("reason"), f"no reason recorded for unscanned {image['image']}"
    record_property("t28_images_total", report["images_total"])
    record_property("t28_images_scanned", report["images_scanned"])
    record_property("t28_images_not_scanned", ",".join(report["images_not_scanned"]))  # type: ignore[arg-type]
    record_property("t28_os_disallowed_licence_components", report["disallowed_total"])
    record_property("t28_os_no_licence_data", report["no_licence_data_total"])
    record_property("t28_exception_file", str(report.get("exception_file")))
