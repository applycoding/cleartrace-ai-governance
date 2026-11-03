from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def test_opa_rego_suite_passes() -> None:
    rego_root = Path(__file__).resolve().parents[2] / "policies" / "rego"
    opa = shutil.which("opa") or "/tmp/opa-install/opa"
    assert Path(opa).exists(), "OPA binary required"
    proc = subprocess.run(
        [opa, "test", str(rego_root), "-v"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
