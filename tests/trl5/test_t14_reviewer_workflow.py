from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

import pytest
from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_db.session import tenant_transaction
from cleartrace_evidence.reviewer import (
    LifecycleState,
    ReviewAction,
    ReviewerWorkflow,
    SeparationOfDutiesError,
    StaleFindingError,
)

from tests.trl5._helpers import TENANT_ALPHA, ensure_principal, ensure_system_with_owner, pg_dsn

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    return pg_dsn()


def test_t14_reviewer_workflow(dsn: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    ledger = AuditLedgerService(
        worm_root=tmp_path_factory.mktemp("worm"),
        signer_key_path=tmp_path_factory.mktemp("keys") / "signer.key",
    )
    reviewer = ReviewerWorkflow()

    def audit_append(
        conn: object,
        *,
        tenant_id: UUID,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        payload: dict[str, object],
    ) -> None:
        ledger.append_event_tx(
            conn,  # type: ignore[arg-type]
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )

    owner_id = ensure_principal(
        dsn, tenant_id=TENANT_ALPHA, role_code="system_owner", email_suffix="t14-owner"
    )
    reviewer_id = ensure_principal(
        dsn, tenant_id=TENANT_ALPHA, role_code="oversight_reviewer", email_suffix="t14-reviewer"
    )
    system_id = ensure_system_with_owner(
        dsn, tenant_id=TENANT_ALPHA, owner_principal_id=owner_id, system_key="SYS-T14"
    )

    finding_ids: list[UUID] = []
    with tenant_transaction(dsn, TENANT_ALPHA) as conn:
        for i in range(60):
            lc = LifecycleState.DRAFT_AUTO if i < 40 else LifecycleState.DRAFT_LLM
            finding_ids.append(
                reviewer.create_finding(
                    conn,
                    tenant_id=TENANT_ALPHA,
                    ai_system_id=system_id,
                    control_id=f"CTRL-{i}",
                    lifecycle_state=lc,
                    outcome_state="not_met",
                    certainty_index=0.85 if lc == LifecycleState.DRAFT_AUTO else 0.5,
                )
            )

    actions_recorded = 0
    self_review_blocked = 0
    stale_conflicts = 0
    draft_llm_effective_without_human = 0

    # 50 validate, 50 reject, 50 modify, 50 annotate
    batches = [
        (ReviewAction.VALIDATE, 50),
        (ReviewAction.REJECT, 50),
        (ReviewAction.MODIFY, 50),
        (ReviewAction.ANNOTATE, 50),
    ]
    idx = 0
    for action, count in batches:
        for _ in range(count):
            finding_id = finding_ids[idx % len(finding_ids)]
            idx += 1
            with tenant_transaction(dsn, TENANT_ALPHA) as conn:
                etag, _before = _load_etag(conn, finding_id)
                try:
                    reviewer.apply_action(
                        conn,
                        tenant_id=TENANT_ALPHA,
                        finding_id=finding_id,
                        if_match=etag,
                        action=action,
                        actor_principal_id=reviewer_id,
                        rationale_en="Review rationale EN"
                        if action == ReviewAction.MODIFY
                        else None,
                        rationale_fr="Justification FR" if action == ReviewAction.MODIFY else None,
                        reason_code="REVIEWER_REJECT" if action == ReviewAction.REJECT else None,
                        modified_outcome="partially_met" if action == ReviewAction.MODIFY else None,
                        audit_append=audit_append,
                    )
                    actions_recorded += 1
                except StaleFindingError:
                    stale_conflicts += 1

    # 40 self-review attempts by owner
    for i in range(40):
        with tenant_transaction(dsn, TENANT_ALPHA) as conn:
            etag, _ = _load_etag(conn, finding_ids[i])
            try:
                reviewer.apply_action(
                    conn,
                    tenant_id=TENANT_ALPHA,
                    finding_id=finding_ids[i],
                    if_match=etag,
                    action=ReviewAction.VALIDATE,
                    actor_principal_id=owner_id,
                    audit_append=audit_append,
                )
            except SeparationOfDutiesError:
                self_review_blocked += 1

    # 20 concurrent stale edits
    target = finding_ids[0]

    def attempt_stale() -> bool:
        with tenant_transaction(dsn, TENANT_ALPHA) as conn:
            etag, _ = _load_etag(conn, target)
            try:
                reviewer.apply_action(
                    conn,
                    tenant_id=TENANT_ALPHA,
                    finding_id=target,
                    if_match='W/"stale-tag"',
                    action=ReviewAction.ANNOTATE,
                    actor_principal_id=reviewer_id,
                    audit_append=audit_append,
                )
                return False
            except StaleFindingError:
                return True

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(attempt_stale) for _ in range(20)]
        stale_conflicts += sum(1 for f in as_completed(futures) if f.result())

    with tenant_transaction(dsn, TENANT_ALPHA) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM finding_version
            WHERE lifecycle_state = 'EFFECTIVE'
              AND finding_id IN (
                SELECT id FROM finding WHERE tenant_id = %s
              )
            """,
            (TENANT_ALPHA,),
        )
        effective_count = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*) FROM finding_version fv
            JOIN finding f ON f.id = fv.finding_id
            WHERE f.tenant_id = %s AND fv.lifecycle_state = 'EFFECTIVE'
              AND EXISTS (
                SELECT 1 FROM finding_version prior
                WHERE prior.finding_id = fv.finding_id
                  AND prior.lifecycle_state = 'DRAFT_LLM'
                  AND prior.version_number < fv.version_number
              )
              AND NOT EXISTS (
                SELECT 1 FROM decision_record dr
                WHERE dr.finding_id = fv.finding_id
                  AND dr.review_action IN ('validate', 'modify')
              )
            """,
            (TENANT_ALPHA,),
        )
        draft_llm_effective_without_human = int(cur.fetchone()[0])

    assert actions_recorded == 200
    assert self_review_blocked == 40
    assert stale_conflicts == 20
    assert draft_llm_effective_without_human == 0
    assert effective_count >= 1


def _load_etag(conn: object, finding_id: UUID) -> tuple[str, int]:
    with conn.cursor() as cur:  # type: ignore[union-attr]
        cur.execute(
            "SELECT etag, current_version_number FROM finding WHERE id = %s",
            (finding_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise LookupError("finding missing")
    return str(row[0]), int(row[1])
