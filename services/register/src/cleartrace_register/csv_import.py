from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from cleartrace_register.precedence import FieldUpdate


class RegisterCsvError(ValueError):
    """The uploaded register CSV is malformed."""


@dataclass(frozen=True, slots=True)
class RegisterImportRow:
    system_key: str
    name_en: str
    name_fr: str
    register_status_en: str
    register_status_fr: str
    primary_users_en: str
    primary_users_fr: str


GC_REGISTER_COLUMN_MAP: dict[str, tuple[int, str, str]] = {
    "Nom du système d'IA / Name of the AI system": (1, "summary", "name"),
    "État / Status": (4, "register_status", "status"),
    "Utilisateurs principaux / Primary users": (6, "primary_users", "users"),
}


def parse_gc_ai_register_csv(
    content: str, *, source_id: str = "gc-ai-register-csv"
) -> list[FieldUpdate]:
    """Parse GC AI Register MVP CSV rows into register field updates (categories 1, 4, 6)."""
    # newline="" lets the csv module handle CR/LF inside quoted fields itself.
    reader = csv.DictReader(io.StringIO(content, newline=""))
    updates: list[FieldUpdate] = []
    now = datetime.now(tz=UTC)
    system_ids: dict[str, UUID] = {}

    try:
        rows = list(reader)
    except csv.Error as exc:
        raise RegisterCsvError(f"CSV could not be parsed: {exc}") from exc

    for row in rows:
        name_en = row.get("Nom du système d'IA / Name of the AI system", "").strip()
        name_fr = row.get("Nom du système d'IA (FR)", name_en).strip() or name_en
        if not name_en:
            continue
        system_key = name_en.lower().replace(" ", "-")[:64]
        if system_key not in system_ids:
            system_ids[system_key] = UUID(int=0)  # placeholder; tests assign real ids

        status_en = row.get("État / Status", "").strip()
        status_fr = row.get("État (FR)", status_en).strip() or status_en
        users_en = row.get("Utilisateurs principaux / Primary users", "").strip()
        users_fr = row.get("Utilisateurs principaux (FR)", users_en).strip() or users_en

        sid = system_ids[system_key]
        updates.append(
            FieldUpdate(
                system_id=sid,
                category_number=1,
                slot_key="summary",
                value_en=name_en,
                value_fr=name_fr,
                source_id=source_id,
                source_tier=1,
                event_time=now,
                received_at=now,
            )
        )
        if status_en:
            updates.append(
                FieldUpdate(
                    system_id=sid,
                    category_number=4,
                    slot_key="register_status",
                    value_en=status_en,
                    value_fr=status_fr,
                    source_id=source_id,
                    source_tier=1,
                    event_time=now,
                    received_at=now,
                )
            )
        if users_en:
            updates.append(
                FieldUpdate(
                    system_id=sid,
                    category_number=6,
                    slot_key="primary_users",
                    value_en=users_en,
                    value_fr=users_fr,
                    source_id=source_id,
                    source_tier=1,
                    event_time=now,
                    received_at=now,
                )
            )
    return updates


def bind_system_ids(updates: list[FieldUpdate], key_to_id: dict[str, UUID]) -> list[FieldUpdate]:
    """Replace placeholder UUIDs using system_key lookup from parallel name field."""
    bound: list[FieldUpdate] = []
    name_by_placeholder: dict[UUID, str] = {}
    for u in updates:
        if u.category_number == 1 and u.slot_key == "summary" and u.value_en:
            name_by_placeholder[u.system_id] = u.value_en.lower().replace(" ", "-")[:64]
    id_map: dict[UUID, UUID] = {}
    for placeholder, key in name_by_placeholder.items():
        id_map[placeholder] = key_to_id.get(key, placeholder)
    for u in updates:
        bound.append(
            FieldUpdate(
                system_id=id_map.get(u.system_id, u.system_id),
                category_number=u.category_number,
                slot_key=u.slot_key,
                value_en=u.value_en,
                value_fr=u.value_fr,
                source_id=u.source_id,
                source_tier=u.source_tier,
                event_time=u.event_time,
                received_at=u.received_at,
                update_id=u.update_id,
            )
        )
    return bound


def missing_intake_marker(value: str | None) -> str:
    if value is None or value.strip() == "":
        return "NEEDS_INTAKE"
    return value
