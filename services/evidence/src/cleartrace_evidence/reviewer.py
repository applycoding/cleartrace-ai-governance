from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Json
from uuid6 import uuid7


class LifecycleState(StrEnum):
    DRAFT_AUTO = "DRAFT_AUTO"
    DRAFT_LLM = "DRAFT_LLM"
    APPROVED_HUMAN = "APPROVED_HUMAN"
    EFFECTIVE = "EFFECTIVE"
    SUPERSEDED = "SUPERSEDED"


class ReviewAction(StrEnum):
    VALIDATE = "validate"
    REJECT = "reject"
    MODIFY = "modify"
    ANNOTATE = "annotate"


@dataclass(frozen=True)
class FindingSnapshot:
    lifecycle_state: str
    outcome_state: str
    certainty_index: float | None
    reason_code: str | None


class ReviewerWorkflow:
    """Reviewer actions with separation of duties and optimistic locking."""

    def create_finding(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        ai_system_id: UUID,
        control_id: str,
        lifecycle_state: LifecycleState,
        outcome_state: str,
        certainty_index: float | None = None,
        reason_code: str | None = None,
    ) -> UUID:
        finding_id = uuid7()
        etag = f'W/"{uuid7()}"'
        version_id = uuid7()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO finding (id, tenant_id, ai_system_id, control_id, current_version_number, etag)
                VALUES (%s, %s, %s, %s, 1, %s)
                """,
                (finding_id, tenant_id, ai_system_id, control_id, etag),
            )
            cur.execute(
                """
                INSERT INTO finding_version (
                  id, tenant_id, finding_id, version_number,
                  lifecycle_state, outcome_state, certainty_index, reason_code
                ) VALUES (%s, %s, %s, 1, %s, %s, %s, %s)
                """,
                (
                    version_id,
                    tenant_id,
                    finding_id,
                    lifecycle_state.value,
                    outcome_state,
                    certainty_index,
                    reason_code,
                ),
            )
        return finding_id

    def _load_finding(
        self, conn: Connection[Any], *, tenant_id: UUID, finding_id: UUID
    ) -> tuple[str, int, str, FindingSnapshot]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.etag, f.current_version_number, f.ai_system_id,
                       fv.lifecycle_state, fv.outcome_state, fv.certainty_index, fv.reason_code
                FROM finding f
                JOIN finding_version fv
                  ON fv.finding_id = f.id AND fv.version_number = f.current_version_number
                WHERE f.tenant_id = %s AND f.id = %s
                """,
                (tenant_id, finding_id),
            )
            row = cur.fetchone()
        if row is None:
            raise LookupError("finding not found")
        etag, version_number, system_id, lc, outcome, certainty, reason = row
        snap = FindingSnapshot(
            lifecycle_state=str(lc),
            outcome_state=str(outcome),
            certainty_index=float(certainty) if certainty is not None else None,
            reason_code=str(reason) if reason is not None else None,
        )
        return str(etag), int(version_number), str(system_id), snap

    def _is_system_owner(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        ai_system_id: UUID,
        actor_principal_id: UUID,
    ) -> bool:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM ai_system_owner
                WHERE tenant_id = %s AND ai_system_id = %s AND principal_id = %s
                """,
                (tenant_id, ai_system_id, actor_principal_id),
            )
            return cur.fetchone() is not None

    def apply_action(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        finding_id: UUID,
        if_match: str | None,
        action: ReviewAction,
        actor_principal_id: UUID,
        rationale_en: str | None = None,
        rationale_fr: str | None = None,
        reason_code: str | None = None,
        modified_outcome: str | None = None,
        audit_append: Any,
    ) -> tuple[str, FindingSnapshot]:
        etag, version_number, system_id, before = self._load_finding(
            conn, tenant_id=tenant_id, finding_id=finding_id
        )
        if if_match is None or if_match != etag:
            raise StaleFindingError(current_etag=etag)

        if action in {ReviewAction.VALIDATE, ReviewAction.MODIFY} and self._is_system_owner(
            conn,
            tenant_id=tenant_id,
            ai_system_id=UUID(system_id),
            actor_principal_id=actor_principal_id,
        ):
            raise SeparationOfDutiesError()

        after = before
        new_lifecycle = before.lifecycle_state
        new_outcome = before.outcome_state
        new_version = version_number

        if action == ReviewAction.ANNOTATE:
            pass
        elif action == ReviewAction.REJECT:
            if not reason_code:
                raise ValueError("reject requires reason_code")
            new_lifecycle = LifecycleState.DRAFT_AUTO.value
        elif action == ReviewAction.VALIDATE:
            if (
                before.lifecycle_state == LifecycleState.DRAFT_LLM.value
                or before.lifecycle_state == LifecycleState.DRAFT_AUTO.value
            ):
                new_lifecycle = LifecycleState.APPROVED_HUMAN.value
            else:
                new_lifecycle = LifecycleState.APPROVED_HUMAN.value
            new_lifecycle = LifecycleState.EFFECTIVE.value
        elif action == ReviewAction.MODIFY:
            if not rationale_en and not rationale_fr:
                raise ValueError("modify requires rationale")
            new_outcome = modified_outcome or before.outcome_state
            new_lifecycle = LifecycleState.EFFECTIVE.value
            new_version = version_number + 1
        else:
            raise ValueError(f"unsupported action {action}")

        new_etag = f'W/"{uuid7()}"'
        after = FindingSnapshot(
            lifecycle_state=new_lifecycle,
            outcome_state=new_outcome,
            certainty_index=before.certainty_index,
            reason_code=reason_code or before.reason_code,
        )

        with conn.cursor() as cur:
            if new_version != version_number:
                cur.execute(
                    """
                    INSERT INTO finding_version (
                      id, tenant_id, finding_id, version_number,
                      lifecycle_state, outcome_state, certainty_index, reason_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid7(),
                        tenant_id,
                        finding_id,
                        new_version,
                        after.lifecycle_state,
                        after.outcome_state,
                        after.certainty_index,
                        after.reason_code,
                    ),
                )
                cur.execute(
                    """
                    UPDATE finding
                    SET current_version_number = %s, etag = %s
                    WHERE id = %s AND tenant_id = %s
                    """,
                    (new_version, new_etag, finding_id, tenant_id),
                )
            elif action != ReviewAction.ANNOTATE:
                cur.execute(
                    """
                    UPDATE finding_version
                    SET lifecycle_state = %s, outcome_state = %s, reason_code = COALESCE(%s, reason_code)
                    WHERE finding_id = %s AND version_number = %s AND tenant_id = %s
                    """,
                    (
                        after.lifecycle_state,
                        after.outcome_state,
                        reason_code,
                        finding_id,
                        version_number,
                        tenant_id,
                    ),
                )
                cur.execute(
                    "UPDATE finding SET etag = %s WHERE id = %s AND tenant_id = %s",
                    (new_etag, finding_id, tenant_id),
                )

            cur.execute(
                """
                INSERT INTO decision_record (
                  id, tenant_id, finding_id, finding_version_number,
                  review_action, actor_principal_id,
                  rationale_en, rationale_fr, reason_code,
                  before_snapshot, after_snapshot
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid7(),
                    tenant_id,
                    finding_id,
                    new_version,
                    action.value,
                    actor_principal_id,
                    rationale_en,
                    rationale_fr,
                    reason_code,
                    Json(json.loads(_snap_json(before))),
                    Json(json.loads(_snap_json(after))),
                ),
            )

        audit_append(
            conn,
            tenant_id=tenant_id,
            actor_id=actor_principal_id,
            action=f"finding.{action.value}",
            resource_type="finding",
            resource_id=finding_id,
            payload={"before": _snap_json(before), "after": _snap_json(after)},
        )
        return new_etag, after

    def bulk_validate_draft_auto(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        finding_ids: list[UUID],
        actor_principal_id: UUID,
        audit_append: Any,
    ) -> int:
        count = 0
        for finding_id in finding_ids:
            _etag, version_number, _system_id, snap = self._load_finding(
                conn, tenant_id=tenant_id, finding_id=finding_id
            )
            if snap.lifecycle_state != LifecycleState.DRAFT_AUTO.value:
                continue
            if snap.certainty_index is None or snap.certainty_index < 0.80:
                continue
            self.apply_action(
                conn,
                tenant_id=tenant_id,
                finding_id=finding_id,
                if_match=self._load_finding(conn, tenant_id=tenant_id, finding_id=finding_id)[0],
                action=ReviewAction.VALIDATE,
                actor_principal_id=actor_principal_id,
                audit_append=audit_append,
            )
            count += 1
        return count


def _snap_json(snap: FindingSnapshot) -> str:
    import json

    return json.dumps(
        {
            "lifecycle_state": snap.lifecycle_state,
            "outcome_state": snap.outcome_state,
            "certainty_index": snap.certainty_index,
            "reason_code": snap.reason_code,
        },
        sort_keys=True,
    )


class StaleFindingError(Exception):
    def __init__(self, *, current_etag: str) -> None:
        super().__init__("stale finding version")
        self.current_etag = current_etag


class SeparationOfDutiesError(Exception):
    pass


class InvalidLifecycleTransition(Exception):
    pass
