#!/usr/bin/env python3
"""Emit a minimal CycloneDX SBOM when Syft is not installed."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "cleartrace",
                "version": "0.1.0",
            },
        },
        "components": [
            {
                "type": "library",
                "name": "cleartrace-workspace",
                "version": "0.1.0",
                "purl": "pkg:generic/cleartrace@0.1.0",
            }
        ],
    }
    (ROOT / "sbom.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("wrote sbom.json (placeholder)")


if __name__ == "__main__":
    main()
