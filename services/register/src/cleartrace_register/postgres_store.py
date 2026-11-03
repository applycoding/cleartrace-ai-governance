from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from psycopg import Connection
from psycopg.types.json import Jsonb
from uuid6 import uuid7

from cleartrace_register.categories import category_by_number
from cleartrace_register.precedence import (
    AppliedValue,
    FieldUpdate,
    PrecedenceEngine,
    PrecedenceResult,
    QuarantineRecord,
)


class PostgresRegisterStore:
    """Persist register values, provenance, and quarantine under tenant RLS."""

    def __init__(self, dsn: str, tenant_id: UUID) -> None:
        self._dsn = dsn
        self._tenant_id = tenant_id
        self.engine = PrecedenceEngine()

    def register_system(self, system_id: UUID, system_key: str) -> None:
        with tenant_transaction(self._dsn, self._tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_system (id, tenant_id, system_key)
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, system_key) DO NOTHING
                """,
                (system_id, self._tenant_id, system_key),
            )

    def ingest(self, update: FieldUpdate) -> PrecedenceResult:
        with tenant_transaction(self._dsn, self._tenant_id) as conn:
            if self._update_already_seen(conn, update.update_id):
                result = PrecedenceResult()
                result.duplicate_noop += 1
                return result
            self._hydrate_key(conn, update.system_id, update.category_number, update.slot_key)
            result = self.engine.apply(update)
            self._persist_result(conn, update, result)
            return result

    def apply_batch(self, updates: list[FieldUpdate]) -> PrecedenceResult:
        ordered = sorted(updates, key=lambda u: (u.event_time, u.received_at, str(u.update_id)))
        combined = PrecedenceResult()
        for update in ordered:
            partial = self.ingest(update)
            combined.applied.extend(partial.applied)
            combined.quarantined.extend(partial.quarantined)
            combined.ignored_lower_tier += partial.ignored_lower_tier
            combined.duplicate_noop += partial.duplicate_noop
        return combined

    def category_filled(self, system_id: UUID, category_number: int) -> bool:
        cat = category_by_number(category_number)
        val = self.get_value(system_id, category_number, cat.primary_slot)
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
        cached = self.engine.get_value(system_id, category_number, slot_key)
        if cached is not None:
            return cached
        with tenant_transaction(self._dsn, self._tenant_id) as conn:
            self._hydrate_key(conn, system_id, category_number, slot_key)
        return self.engine.get_value(system_id, category_number, slot_key)

    @property
    def quarantine_items(self) -> list[QuarantineRecord]:
        return self.engine.quarantine_items

    def _update_already_seen(self, conn: Connection[Any], update_id: UUID) -> bool:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM source_record
                WHERE tenant_id = %s AND payload->>'update_id' = %s
                LIMIT 1
                """,
                (self._tenant_id, str(update_id)),
            )
            return cur.fetchone() is not None

    def _hydrate_key(
        self, conn: Connection[Any], system_id: UUID, category_number: int, slot_key: str
    ) -> None:
        key = (system_id, category_number, slot_key)
        if self.engine.get_value(system_id, category_number, slot_key) is not None:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT value_en, value_fr, source_id, source_tier, event_time, valid_from, id
                FROM register_category_value
                WHERE tenant_id = %s AND ai_system_id = %s
                  AND category_number = %s AND slot_key = %s AND valid_to IS NULL
                LIMIT 1
                """,
                (self._tenant_id, system_id, category_number, slot_key),
            )
            row = cur.fetchone()
        if row is None:
            return
        value_en, value_fr, source_id, source_tier, event_time, valid_from, row_id = row
        applied = AppliedValue(
            system_id=system_id,
            category_number=category_number,
            slot_key=slot_key,
            value_en=value_en,
            value_fr=value_fr,
            source_id=source_id,
            source_tier=int(source_tier),
            event_time=event_time,
            valid_from=valid_from,
            update_id=UUID(str(row_id)),
        )
        self.engine._values[key] = applied

    def _persist_result(
        self, conn: Connection[Any], update: FieldUpdate, result: PrecedenceResult
    ) -> None:
        source_id = uuid7()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO source_record (
                  id, tenant_id, source_id, payload, received_at, event_time
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    source_id,
                    self._tenant_id,
                    update.source_id,
                    Jsonb(
                        {
                            "update_id": str(update.update_id),
                            "category": update.category_number,
                            "slot": update.slot_key,
                        }
                    ),
                    update.received_at,
                    update.event_time,
                ),
            )
            for record in result.quarantined:
                cur.execute(
                    """
                    INSERT INTO quarantine_item (
                      id, tenant_id, ai_system_id, field_path, reason,
                      source_record_id, payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid7(),
                        self._tenant_id,
                        record.system_id,
                        record.field_path,
                        record.reason.value,
                        source_id,
                        Jsonb({"update_id": str(record.update.update_id)}),
                    ),
                )
            for applied in result.applied:
                cur.execute(
                    """
                    UPDATE register_category_value
                    SET valid_to = %s
                    WHERE tenant_id = %s AND ai_system_id = %s
                      AND category_number = %s AND slot_key = %s AND valid_to IS NULL
                    """,
                    (
                        applied.valid_from,
                        self._tenant_id,
                        applied.system_id,
                        applied.category_number,
                        applied.slot_key,
                    ),
                )
                value_id = uuid7()
                cur.execute(
                    """
                    INSERT INTO register_category_value (
                      id, tenant_id, ai_system_id, category_number, slot_key,
                      value_en, value_fr, needs_intake, source_id, source_tier,
                      event_time, valid_from, valid_to, recorded_at
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, %s, false, %s, %s, %s, %s, NULL, %s
                    )
                    """,
                    (
                        value_id,
                        self._tenant_id,
                        applied.system_id,
                        applied.category_number,
                        applied.slot_key,
                        applied.value_en,
                        applied.value_fr,
                        applied.source_id,
                        applied.source_tier,
                        applied.event_time,
                        applied.valid_from,
                        datetime.now(tz=UTC),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO field_provenance (
                      id, tenant_id, register_value_id, source_record_id, applied_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (uuid7(), self._tenant_id, value_id, source_id, datetime.now(tz=UTC)),
                )
