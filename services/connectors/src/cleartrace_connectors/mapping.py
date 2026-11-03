from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cleartrace_register.categories import GOVERNANCE_CATEGORIES
from cleartrace_register.precedence import FieldUpdate


@dataclass(frozen=True, slots=True)
class MappedField:
    category_number: int
    slot_key: str
    value_en: str | None
    value_fr: str | None


def apply_field_mapping(
    payload: dict[str, Any],
    field_mapping: dict[str, Any],
    *,
    source_id: str,
    source_tier: int,
    system_id: UUID,
) -> list[FieldUpdate]:
    now = datetime.now(tz=UTC)
    updates: list[FieldUpdate] = []
    for source_path, target in field_mapping.items():
        value = _resolve_path(payload, source_path)
        if value is None:
            continue
        category_number, slot_key = _parse_target(target)
        value_en, value_fr = _bilingual(value)
        updates.append(
            FieldUpdate(
                system_id=system_id,
                category_number=category_number,
                slot_key=slot_key,
                value_en=value_en,
                value_fr=value_fr,
                source_id=source_id,
                source_tier=source_tier,
                event_time=now,
                received_at=now,
            )
        )
    return updates


def fill_all_categories(
    system_id: UUID,
    *,
    source_id: str,
    values_by_category: dict[int, tuple[str, str]],
) -> list[FieldUpdate]:
    """Ensure each of the 15 categories has a primary slot value."""
    now = datetime.now(tz=UTC)
    updates: list[FieldUpdate] = []
    for cat in GOVERNANCE_CATEGORIES:
        en, fr = values_by_category.get(cat.number, ("NEEDS_INTAKE", "NEEDS_INTAKE"))
        updates.append(
            FieldUpdate(
                system_id=system_id,
                category_number=cat.number,
                slot_key=cat.primary_slot,
                value_en=en,
                value_fr=fr,
                source_id=source_id,
                source_tier=1,
                event_time=now,
                received_at=now,
            )
        )
    return updates


def _parse_target(target: Any) -> tuple[int, str]:
    if isinstance(target, str) and "." in target:
        cat_str, slot = target.split(".", 1)
        return int(cat_str), slot
    if isinstance(target, dict):
        return int(target["category"]), str(target["slot"])
    msg = f"Invalid mapping target: {target}"
    raise ValueError(msg)


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _bilingual(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        return str(value.get("en") or ""), str(value.get("fr") or value.get("en") or "")
    text = str(value)
    return text, text


def parse_json_bytes(data: bytes) -> dict[str, Any]:
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        msg = "Expected JSON object"
        raise ValueError(msg)
    return parsed
