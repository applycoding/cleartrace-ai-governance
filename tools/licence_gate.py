#!/usr/bin/env python3
"""Fail the build if shipped dependency licences are not permissive."""

from __future__ import annotations

from pathlib import Path

DISALLOWED = (
    "AGPL",
    "GPL",
    "LGPL",
    "SSPL",
    "BSL",
    "ELASTIC",
    "Elastic License",
    "MPL-2.0",
    "BUSL",
)

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "pyproject.toml",
    ROOT / "packages",
    ROOT / "services",
    ROOT / "db",
    ROOT / "web" / "package.json",
]


def scan_file(path: Path) -> list[str]:
    hits: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for token in DISALLOWED:
        if token in text:
            hits.append(f"{path}: contains disallowed licence token {token}")
    return hits


def main() -> int:
    problems: list[str] = []
    for target in TARGETS:
        if target.is_file():
            problems.extend(scan_file(target))
        elif target.is_dir():
            for file in target.rglob("*"):
                if file.suffix in {".toml", ".py", ".json", ".md", ".yaml", ".yml"}:
                    problems.extend(scan_file(file))
    if problems:
        print("\n".join(problems))
        return 1
    print("licence gate: OK (no disallowed tokens in scanned shipped paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
