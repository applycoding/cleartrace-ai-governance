from __future__ import annotations

import os
from uuid import UUID

import pytest
from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_db.session import tenant_transaction
from cleartrace_evidence.authorization import DEFAULT_REQUIRED_ROLES, ensure_evidence_specs
from cleartrace_evidence.constants import ARTEFACT_CLASSES
from cleartrace_evidence.store import EvidenceStoreService

from tests.trl5._helpers import TENANT_ALPHA, ensure_principal, migrator_tenant_tx, pg_dsn

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    if not os.environ.get("CLEARTRACE_TEST_DSN") and not _pg_ready():
        pytest.skip("Postgres stack not running")
    return pg_dsn()


def _pg_ready() -> bool:
    import socket

    host = os.environ.get("CLEARTRACE_PGBOUNCER_HOST", "127.0.0.1")
    port = int(os.environ.get("CLEARTRACE_PGBOUNCER_PORT", "6432"))
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def test_t12_evidence_store_and_unauthorized_mandatory(
    dsn: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    storage = tmp_path_factory.mktemp("evidence")
    store = EvidenceStoreService(storage)
    ledger = AuditLedgerService(
        worm_root=tmp_path_factory.mktemp("worm"),
        signer_key_path=tmp_path_factory.mktemp("keys") / "signer.key",
    )
    classes = sorted(ARTEFACT_CLASSES)
    stored = 0
    unauthorized_count = 0
    unauthorized_satisfy = 0

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

    with migrator_tenant_tx(TENANT_ALPHA) as conn:
        ensure_evidence_specs(conn, TENANT_ALPHA)

    role_principals: dict[str, UUID] = {}
    for role in {
        "assessor",
        "approver",
        "system_owner",
        "oversight_reviewer",
        "auditor",
        "tenant_admin",
    }:
        role_principals[role] = ensure_principal(
            dsn, tenant_id=TENANT_ALPHA, role_code=role, email_suffix=f"t12-{role}"
        )

    unauthorized_principal = ensure_principal(
        dsn, tenant_id=TENANT_ALPHA, role_code="read_only_viewer", email_suffix="t12-unauth"
    )

    # 400 authorized + 100 unauthorized across classes (500 total)
    for i in range(500):
        artefact_class = classes[i % len(classes)]
        if i >= 400:
            principal = unauthorized_principal
            unauthorized_count += 1
        else:
            required = DEFAULT_REQUIRED_ROLES.get(artefact_class, ("system_owner",))
            principal = role_principals[required[0]]
        payload = f"artefact-{i}".encode()
        with tenant_transaction(dsn, TENANT_ALPHA) as conn:
            version_id = store.store_artefact_tx(
                conn,
                tenant_id=TENANT_ALPHA,
                principal_id=principal,
                payload=payload,
                metadata={
                    "artefact_class": artefact_class,
                    "title_en": f"Title EN {i}",
                    "title_fr": f"Titre FR {i}",
                    "media_type": "text/plain",
                },
                audit_append=audit_append,
            )
            stored += 1
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sha256, submitted_by, submitter_role_at_time, authorized_submitter
                    FROM evidence_version WHERE id = %s
                    """,
                    (version_id,),
                )
                row = cur.fetchone()
            assert row is not None
            sha256, submitted_by, role_at, authorized = row
            assert sha256
            assert submitted_by == principal
            assert role_at
            if (
                store.can_satisfy_mandatory(
                    conn, tenant_id=TENANT_ALPHA, evidence_version_id=version_id
                )
                and not authorized
            ):
                unauthorized_satisfy += 1

    assert stored == 500
    assert unauthorized_count == 100
    assert unauthorized_satisfy == 0
