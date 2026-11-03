from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cleartrace_register.categories import category_by_number
from cleartrace_register.precedence import AppliedValue, FieldUpdate, PrecedenceEngine


class AppliedHistoryEntry:
    __slots__ = ("system_id", "category_number", "slot_key", "value_en", "value_fr", "at")

    def __init__(
        self,
        *,
        system_id: UUID,
        category_number: int,
        slot_key: str,
        value_en: str | None,
        value_fr: str | None,
        at: datetime,
    ) -> None:
        self.system_id = system_id
        self.category_number = category_number
        self.slot_key = slot_key
        self.value_en = value_en
        self.value_fr = value_fr
        self.at = at


class MemoryRegisterStore:
    """Unit-test fake only — not used on TRL integration paths."""

    def __init__(self) -> None:
        self.engine = PrecedenceEngine()
        self.system_keys: dict[UUID, str] = {}
        self.groups: dict[str, set[UUID]] = {}
        self.history: list[AppliedHistoryEntry] = []

    def register_system(self, system_id: UUID, system_key: str) -> None:
        self.system_keys[system_id] = system_key

    def add_group_member(self, group_code: str, system_id: UUID) -> None:
        self.groups.setdefault(group_code, set()).add(system_id)

    def ingest(self, update: FieldUpdate) -> None:
        result = self.engine.apply(update)
        for applied in result.applied:
            self.history.append(
                AppliedHistoryEntry(
                    system_id=applied.system_id,
                    category_number=applied.category_number,
                    slot_key=applied.slot_key,
                    value_en=applied.value_en,
                    value_fr=applied.value_fr,
                    at=applied.valid_from,
                )
            )

    def apply_batch(self, updates: list[FieldUpdate]) -> None:
        result = self.engine.apply_batch(updates)
        for applied in result.applied:
            self.history.append(
                AppliedHistoryEntry(
                    system_id=applied.system_id,
                    category_number=applied.category_number,
                    slot_key=applied.slot_key,
                    value_en=applied.value_en,
                    value_fr=applied.value_fr,
                    at=applied.valid_from,
                )
            )

    def category_filled(self, system_id: UUID, category_number: int) -> bool:
        cat = category_by_number(category_number)
        val = self.engine.get_value(system_id, category_number, cat.primary_slot)
        if val is None:
            return False
        return not (
            val.value_en in (None, "", "NEEDS_INTAKE")
            and val.value_fr in (None, "", "NEEDS_INTAKE")
        )

    def filled_category_count(self, system_id: UUID) -> int:
        return sum(1 for n in range(1, 16) if self.category_filled(system_id, n))

    def get_value(
        self, system_id: UUID, category_number: int, slot_key: str
    ) -> AppliedValue | None:
        return self.engine.get_value(system_id, category_number, slot_key)
