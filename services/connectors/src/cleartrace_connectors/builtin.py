from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_mlflow_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "mlflow" / f"{name}.json")


def load_otel_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "otel" / f"{name}.json")


def load_openlineage_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "openlineage" / f"{name}.json")


def load_aia_json_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "aia" / f"{name}.json")


def load_ticket_simulator_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "ticket_simulator" / f"{name}.json")


def load_generic_csv_fixture(name: str) -> dict[str, Any]:
    return _read_json(_FIXTURES / "generic_csv" / f"{name}.json")


def _read_json(path: Path) -> dict[str, Any]:
    # Fixture names come from API callers: never read outside the fixtures folder.
    resolved = path.resolve()
    if not resolved.is_relative_to(_FIXTURES):
        msg = "Fixture not found"
        raise FileNotFoundError(msg)
    path = resolved
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = "Fixture must be a JSON object"
        raise ValueError(msg)
    return data
