from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cleartrace_register.postgres_store import PostgresRegisterStore
from cleartrace_register.precedence import FieldUpdate, QuarantineReason
from uuid6 import uuid7


def _update(
    *,
    system_id: UUID,
    tier: int,
    source: str,
    event_time: datetime,
    received_at: datetime,
    value: str,
    slot: str = "register_status",
    category: int = 4,
) -> FieldUpdate:
    return FieldUpdate(
        system_id=system_id,
        category_number=category,
        slot_key=slot,
        value_en=value,
        value_fr=value,
        source_id=source,
        source_tier=tier,
        event_time=event_time,
        received_at=received_at,
    )


def test_t04_thousand_interleaved_updates_with_quarantine(
    trl_dsn: str, trl_tenant_id: UUID
) -> None:
    store = PostgresRegisterStore(trl_dsn, trl_tenant_id)
    system_id = uuid7()
    store.register_system(system_id, f"t04-{system_id}")
    base = datetime(2025, 1, 1, tzinfo=UTC)
    updates: list[FieldUpdate] = []
    skew_targets: list[FieldUpdate] = []
    conflict_targets: list[FieldUpdate] = []

    for i in range(1000):
        event_time = base + timedelta(seconds=i)
        received_at = event_time + timedelta(seconds=1)
        tier = 1 if i % 2 == 0 else 2
        source = f"source-{tier}"
        value = f"v-{i}"
        update = _update(
            system_id=system_id,
            tier=tier,
            source=source,
            event_time=event_time,
            received_at=received_at,
            value=value,
            slot="summary" if i % 17 == 0 else "register_status",
            category=1 if i % 17 == 0 else 4,
        )
        updates.append(update)

    for j in range(50):
        idx = 100 + j * 7
        skewed = _update(
            system_id=system_id,
            tier=1,
            source="skew-source",
            event_time=base + timedelta(seconds=idx),
            received_at=base + timedelta(seconds=idx) + timedelta(seconds=400),
            value=f"skew-{j}",
        )
        skew_targets.append(skewed)
        updates.append(skewed)

    for k in range(50):
        idx = 200 + k * 9
        event_time = base + timedelta(seconds=idx)
        first = _update(
            system_id=system_id,
            tier=1,
            source="conflict-a",
            event_time=event_time,
            received_at=event_time,
            value=f"conflict-{k}-a",
        )
        second = _update(
            system_id=system_id,
            tier=1,
            source="conflict-b",
            event_time=event_time,
            received_at=event_time,
            value=f"conflict-{k}-b",
        )
        conflict_targets.extend([first, second])
        updates.extend([first, second])

    rng = random.Random(42)
    rng.shuffle(updates)

    result = store.apply_batch(updates)
    applied_ids = {a.update_id for a in result.applied}
    assert len(applied_ids) == len(result.applied), "double-apply detected"

    quarantined_ids = {q.update.update_id for q in store.quarantine_items}
    for skew in skew_targets:
        assert skew.update_id in quarantined_ids
        reason = next(q for q in store.quarantine_items if q.update.update_id == skew.update_id)
        assert reason.reason == QuarantineReason.CLOCK_SKEW

    for conflict in conflict_targets[1::2]:
        assert conflict.update_id in quarantined_ids
        reason = next(q for q in store.quarantine_items if q.update.update_id == conflict.update_id)
        assert reason.reason == QuarantineReason.EQUAL_TIER_CONFLICT

    assert len(skew_targets) == 50
    assert len([q for q in store.quarantine_items if q.reason == QuarantineReason.CLOCK_SKEW]) == 50
    assert (
        len([q for q in store.quarantine_items if q.reason == QuarantineReason.EQUAL_TIER_CONFLICT])
        >= 50
    )

    total_processed = (
        len(result.applied)
        + len(result.quarantined)
        + result.ignored_lower_tier
        + result.duplicate_noop
    )
    assert total_processed == len(updates)
