from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cleartrace_engine.types import ControlContext


class PackValidationError(Exception):
    pass


def load_pack(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PackValidationError("Pack root must be a mapping")
    required = ("slug", "obligation_type", "source_url_en", "source_url_fr", "controls")
    for key in required:
        if key not in data:
            raise PackValidationError(f"Missing required pack field: {key}")
    if data.get("needs_second_reader_recheck") is not True:
        raise PackValidationError("Pack must set needs_second_reader_recheck: true")
    return data


def pack_to_oscal_catalog(pack: dict[str, Any]) -> dict[str, Any]:
    controls = []
    for ctrl in pack["controls"]:
        controls.append(
            {
                "id": ctrl["control_key"],
                "title": ctrl["title_en"],
                "props": [
                    {"name": "title-fr", "value": ctrl["title_fr"]},
                    {"name": "clause-ref", "value": ctrl["clause_ref"]},
                    {
                        "name": "obligation-type",
                        "value": ctrl.get("obligation_type", pack["obligation_type"]),
                    },
                    {"name": "source-url", "value": pack["source_url_en"]},
                ],
            }
        )
    return {
        "catalog": {
            "uuid": pack.get("catalog_uuid", "00000000-0000-4000-8000-000000000001"),
            "metadata": {
                "title": pack["name_en"],
                "version": pack.get("version", "1.0.0"),
                "props": [
                    {"name": "title-fr", "value": pack["name_fr"]},
                    {"name": "source-url-fr", "value": pack["source_url_fr"]},
                ],
            },
            "controls": controls,
        }
    }


def control_context_from_pack(pack: dict[str, Any], control: dict[str, Any]) -> ControlContext:
    return ControlContext(
        control_id=control["control_key"],
        control_version=pack.get("version", "1.0.0"),
        requirement_en=control["title_en"],
        requirement_fr=control["title_fr"],
        clause_ref=control["clause_ref"],
        source_url=pack["source_url_en"],
        remediation_en=control.get("remediation_en", "Review the cited requirement."),
        remediation_fr=control.get("remediation_fr", "Examiner l'exigence citée."),
    )


def list_packs(packs_root: Path) -> list[Path]:
    return sorted(packs_root.glob("*/pack.yaml"))
