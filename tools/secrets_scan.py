#!/usr/bin/env python3
"""Lightweight secrets scan when gitleaks is unavailable in CI."""

from __future__ import annotations

import re
from pathlib import Path

PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
]

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", ".data", "node_modules", "uv.lock"}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix in {".png", ".jpg", ".gz", ".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{path}: matched {pattern.pattern}")
    if findings:
        print("\n".join(findings))
        return 1
    print("secrets scan: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
