from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ConnectorManifest:
    name: str
    version: str
    direction: str
    scopes: tuple[str, ...]
    field_mapping: dict[str, Any]
    source_tiers: dict[str, int]
    schedule: str | None = None
    destinations: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConnectorManifest:
        return cls(
            name=str(data["name"]),
            version=str(data["version"]),
            direction=str(data["direction"]),
            scopes=tuple(str(s) for s in data.get("scopes", [])),
            field_mapping=dict(data.get("field_mapping", {})),
            source_tiers={str(k): int(v) for k, v in data.get("source_tiers", {}).items()},
            schedule=data.get("schedule"),
            destinations=tuple(data.get("destinations", [])),
        )

    @classmethod
    def load_path(cls, path: Path) -> ConnectorManifest:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) if path.suffix in (".yaml", ".yml") else json.loads(raw)
        if not isinstance(data, dict):
            msg = "Manifest must be a mapping"
            raise ValueError(msg)
        return cls.from_dict(data)


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("name", "version", "direction", "scopes", "field_mapping"):
        if key not in data:
            errors.append(f"Missing required field: {key}")
    if data.get("direction") not in ("pull", "push", "both"):
        errors.append("Invalid direction")
    return errors
