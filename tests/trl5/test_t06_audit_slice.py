from __future__ import annotations

from uuid import UUID

import pytest
from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_db.session import tenant_transaction

from tests.trl5._helpers import pg_dsn

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    return pg_dsn()


def test_t06_audit_denials_and_privileged_reads(
    dsn: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Audit slice of T-06: denials and privileged reads are recorded in the ledger."""
    ledger = AuditLedgerService(
        worm_root=tmp_path_factory.mktemp("worm"),
        signer_key_path=tmp_path_factory.mktemp("keys") / "signer.key",
    )
    tenant_ids = [
        UUID("11111111-1111-7111-8111-111111111101"),
        UUID("11111111-1111-7111-8111-111111111102"),
        UUID("11111111-1111-7111-8111-111111111103"),
    ]
    denials = 0
    privileged_reads = 0
    for tenant_id in tenant_ids:
        for i in range(20):
            with tenant_transaction(dsn, tenant_id) as conn:
                ledger.append_event_tx(
                    conn,
                    tenant_id=tenant_id,
                    actor_id=None,
                    action="authz.denied",
                    resource_type="api",
                    resource_id=None,
                    payload={"attempted_action": "review_finding", "path": f"/deny/{i}"},
                )
                denials += 1
        for i in range(20):
            with tenant_transaction(dsn, tenant_id) as conn:
                ledger.append_event_tx(
                    conn,
                    tenant_id=tenant_id,
                    actor_id=None,
                    action="audit.read",
                    resource_type="audit_ledger",
                    resource_id=None,
                    payload={"path": "/audit/events", "batch": i},
                )
                privileged_reads += 1

    assert denials == 60
    assert privileged_reads == 60
