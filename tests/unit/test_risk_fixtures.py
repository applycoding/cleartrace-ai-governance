from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_risk_fixture_manifest_checksums() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "services" / "risk" / "tools" / "verify_fixtures.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
