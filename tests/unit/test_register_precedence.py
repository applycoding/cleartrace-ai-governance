from __future__ import annotations

from cleartrace_register.precedence import FieldUpdate, PrecedenceEngine, QuarantineReason, utc_now
from uuid6 import uuid7


def test_lower_tier_does_not_overwrite_higher_tier() -> None:
    engine = PrecedenceEngine()
    system_id = uuid7()
    now = utc_now()
    first = FieldUpdate(
        system_id=system_id,
        category_number=5,
        slot_key="funding_status",
        value_en="Funded",
        value_fr="Financé",
        source_id="erp",
        source_tier=1,
        event_time=now,
        received_at=now,
    )
    second = FieldUpdate(
        system_id=system_id,
        category_number=5,
        slot_key="funding_status",
        value_en="Manual guess",
        value_fr="Estimation",
        source_id="manual",
        source_tier=2,
        event_time=now,
        received_at=now,
    )
    engine.apply(first)
    result = engine.apply(second)
    assert result.ignored_lower_tier == 1
    current = engine.get_value(system_id, 5, "funding_status")
    assert current is not None
    assert current.value_en == "Funded"


def test_equal_tier_conflict_quarantined() -> None:
    engine = PrecedenceEngine()
    system_id = uuid7()
    now = utc_now()
    a = FieldUpdate(
        system_id=system_id,
        category_number=4,
        slot_key="register_status",
        value_en="Pilot",
        value_fr="Pilote",
        source_id="registry-a",
        source_tier=1,
        event_time=now,
        received_at=now,
    )
    b = FieldUpdate(
        system_id=system_id,
        category_number=4,
        slot_key="register_status",
        value_en="Production",
        value_fr="Production",
        source_id="registry-b",
        source_tier=1,
        event_time=now,
        received_at=now,
    )
    engine.apply(a)
    result = engine.apply(b)
    assert len(result.quarantined) == 1
    assert result.quarantined[0].reason == QuarantineReason.EQUAL_TIER_CONFLICT
