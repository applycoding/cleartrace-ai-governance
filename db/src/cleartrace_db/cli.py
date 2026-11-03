from __future__ import annotations

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"


def _alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Alembic migrations for ClearTrace")
    parser.add_argument("command", choices=["upgrade", "downgrade", "current", "history"])
    parser.add_argument("revision", nargs="?", default="head")
    args = parser.parse_args()
    os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
    os.chdir(ROOT)
    cfg = _alembic_config()
    if args.command == "upgrade":
        command.upgrade(cfg, args.revision)
    elif args.command == "downgrade":
        command.downgrade(cfg, args.revision)
    elif args.command == "current":
        command.current(cfg)
    elif args.command == "history":
        command.history(cfg)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
