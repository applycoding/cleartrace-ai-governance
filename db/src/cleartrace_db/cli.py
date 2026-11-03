from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Alembic migrations for ClearTrace")
    parser.add_argument("command", choices=["upgrade", "downgrade", "current", "history"])
    parser.add_argument("revision", nargs="?", default="head")
    args = parser.parse_args()
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    cmd = ["alembic", "-c", str(ALEMBIC_INI), args.command, args.revision]
    raise SystemExit(subprocess.call(cmd, cwd=ROOT, env=env))
