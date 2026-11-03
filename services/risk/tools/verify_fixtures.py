#!/usr/bin/env python3
"""Verify frozen risk fixtures against manifest.json SHA-256 digests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fixtures" / "manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []
    for entry in manifest["fixtures"]:
        rel = entry["path"]
        expected = entry["sha256"]
        path = ROOT / "fixtures" / rel
        if not path.is_file():
            problems.append(f"missing file: {rel}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            problems.append(f"checksum mismatch for {rel}: expected {expected}, got {actual}")
    if problems:
        print("\n".join(problems))
        return 1
    print(f"risk fixtures: OK ({len(manifest['fixtures'])} files verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
