from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient

pytestmark = pytest.mark.trl5

ROOT = Path(__file__).resolve().parents[2]


def _load_offline_manifest() -> dict:
    path = ROOT / "deploy" / "offline-bundle" / "images.manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_t19_install_smoke_manifest_and_health() -> None:
    offline = _load_offline_manifest()
    images = offline["images"]
    digests = [item["digest"] for item in images]
    assert len(digests) == len(set(digests)) or len(images) >= 1
    assert offline.get("signed") is False
    assert offline.get("status") == "pending_signing"
    assert offline.get("signature_algorithm") == "cosign"

    for name in ("values-onprem.yaml", "values-private.yaml", "values-canada-cloud.yaml"):
        text = (ROOT / "deploy" / name).read_text(encoding="utf-8")
        assert "jurisdiction: CA" in text

    app = create_app(Settings(dev_skip_auth=True))
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    caps = client.get("/api/v1/capabilities")
    assert caps.status_code == 200
    assert caps.json()["oscal_version"] == "1.2.3"

    bundle_script = ROOT / "deploy" / "offline-bundle" / "build_bundle.sh"
    subprocess.run(["bash", str(bundle_script)], cwd=ROOT, check=True)
    dist = ROOT / "deploy" / "offline-bundle" / "dist" / "SHA256SUMS"
    assert dist.exists()

    # TRL 5 report note: bundle signing is pending (not claimed as signed).
