"""Run tests/integration/test_rls_leak.py and test_bitemporal.py against local stack."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    stack = ROOT / "scripts" / "dev_stack.sh"
    if os.environ.get("CLEARTRACE_SKIP_STACK") != "1":
        subprocess.check_call(["bash", str(stack)], cwd=ROOT)
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "pytest", "-q", "tests/integration"],
            cwd=ROOT,
            env={**os.environ, "CLEARTRACE_SKIP_STACK": "1"},
        )
    )


if __name__ == "__main__":
    main()
