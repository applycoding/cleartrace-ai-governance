from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from uuid6 import uuid7


class QuarantineReason(StrEnum):
    CLOCK_SKEW = "CLOCK_SKEW"
    EQUAL_TIER_CONFLICT = "EQUAL_TIER_CONFLICT"


@dataclass(frozen=True, slots=True)
class FieldUpdate:
    system_id: UUID
    category_number: int
    slot_key: str
    value_en: str | None
    value_fr: str | None
    source_id: str
    source_tier: int
    event_time: datetime
    received_at: datetime
    update_id: UUID = field(default_factory=uuid7)


@dataclass(frozen=True, slots=True)
class AppliedValue:
    system_id: UUID
    category_number: int
    slot_key: str
    value_en: str | None
    value_fr: str | None
    source_id: str
    source_tier: int
    event_time: datetime
    valid_from: datetime
    update_id: UUID


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    system_id: UUID
    field_path: str
    reason: QuarantineReason
    update: FieldUpdate


@dataclass
class PrecedenceResult:
    applied: list[AppliedValue] = field(default_factory=list)
    quarantined: list[QuarantineRecord] = field(default_factory=list)
    ignored_lower_tier: int = 0
    duplicate_noop: int = 0


SKEW_THRESHOLD = timedelta(seconds=300)


class PrecedenceEngine:
    """Field-level source precedence with quarantine for skew and equal-tier conflicts."""

    def __init__(self) -> None:
        self._values: dict[tuple[UUID, int, str], AppliedValue] = {}
        self._processed_updates: set[UUID] = set()
        self._quarantine: list[QuarantineRecord] = []

    @property
    def quarantine_items(self) -> list[QuarantineRecord]:
        return list(self._quarantine)

    def get_value(
        self, system_id: UUID, category_number: int, slot_key: str
    ) -> AppliedValue | None:
        return self._values.get((system_id, category_number, slot_key))

    def apply(self, update: FieldUpdate) -> PrecedenceResult:
        result = PrecedenceResult()
        if update.update_id in self._processed_updates:
            result.duplicate_noop += 1
            return result

        skew = abs(update.received_at - update.event_time)
        if skew > SKEW_THRESHOLD:
            record = QuarantineRecord(
                system_id=update.system_id,
                field_path=f"{update.category_number}/{update.slot_key}",
                reason=QuarantineReason.CLOCK_SKEW,
                update=update,
            )
            self._quarantine.append(record)
            result.quarantined.append(record)
            self._processed_updates.add(update.update_id)
            return result

        key = (update.system_id, update.category_number, update.slot_key)
        current = self._values.get(key)

        if current is not None:
            if update.source_tier > current.source_tier:
                result.ignored_lower_tier += 1
                self._processed_updates.add(update.update_id)
                return result
            if update.source_tier < current.source_tier:
                pass
            elif update.event_time < current.event_time:
                result.ignored_lower_tier += 1
                self._processed_updates.add(update.update_id)
                return result
            elif (
                update.event_time == current.event_time
                and update.source_tier == current.source_tier
            ):
                same_en = (update.value_en or "") == (current.value_en or "")
                same_fr = (update.value_fr or "") == (current.value_fr or "")
                if same_en and same_fr and update.source_id == current.source_id:
                    result.duplicate_noop += 1
                    self._processed_updates.add(update.update_id)
                    return result
                record = QuarantineRecord(
                    system_id=update.system_id,
                    field_path=f"{update.category_number}/{update.slot_key}",
                    reason=QuarantineReason.EQUAL_TIER_CONFLICT,
                    update=update,
                )
                self._quarantine.append(record)
                result.quarantined.append(record)
                self._processed_updates.add(update.update_id)
                return result
            elif (
                update.source_tier == current.source_tier
                and update.event_time > current.event_time
                and (
                    (update.value_en or "") != (current.value_en or "")
                    or (update.value_fr or "") != (current.value_fr or "")
                )
            ):
                record = QuarantineRecord(
                    system_id=update.system_id,
                    field_path=f"{update.category_number}/{update.slot_key}",
                    reason=QuarantineReason.EQUAL_TIER_CONFLICT,
                    update=update,
                )
                self._quarantine.append(record)
                result.quarantined.append(record)
                self._processed_updates.add(update.update_id)
                return result

        applied = AppliedValue(
            system_id=update.system_id,
            category_number=update.category_number,
            slot_key=update.slot_key,
            value_en=update.value_en,
            value_fr=update.value_fr,
            source_id=update.source_id,
            source_tier=update.source_tier,
            event_time=update.event_time,
            valid_from=update.event_time,
            update_id=update.update_id,
        )
        self._values[key] = applied
        self._processed_updates.add(update.update_id)
        result.applied.append(applied)
        return result

    def apply_batch(self, updates: list[FieldUpdate]) -> PrecedenceResult:
        ordered = sorted(updates, key=lambda u: (u.event_time, u.received_at, str(u.update_id)))
        combined = PrecedenceResult()
        for update in ordered:
            partial = self.apply(update)
            combined.applied.extend(partial.applied)
            combined.quarantined.extend(partial.quarantined)
            combined.ignored_lower_tier += partial.ignored_lower_tier
            combined.duplicate_noop += partial.duplicate_noop
        return combined


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
