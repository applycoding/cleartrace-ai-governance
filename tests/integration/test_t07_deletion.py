from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from cleartrace_core_api.data_policy.models import DeletionCertificateStatus, RetentionRuleBody
from cleartrace_core_api.data_policy.service import DataPolicyService
from cleartrace_db.session import tenant_transaction

pytestmark = pytest.mark.trl5

TENANT = UUID("11111111-1111-7111-8111-111111111101")
EVIDENCE_RETENTION = RetentionRuleBody(
    artefact_class="evidence",
    configured_retention_days=30,
    statutory_floor_days=730,
)


def _dsn() -> str:
    return os.environ.get(
        "CLEARTRACE_TEST_DSN",
        "postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace",
    )


@pytest.fixture(scope="module")
def dsn() -> str:
    return _dsn()


def test_t07_retention_legal_hold_deletion_certificates(dsn: str) -> None:
    svc = DataPolicyService(dsn)
    svc.upsert_retention(TENANT, [EVIDENCE_RETENTION])
    old = datetime.now(tz=UTC) - timedelta(days=900)
    held_id = svc.store_encrypted_payload(
        TENANT, artefact_class="evidence", plaintext=b"held-record", last_used_at=old
    )
    due_id = svc.store_encrypted_payload(
        TENANT, artefact_class="evidence", plaintext=b"due-record", last_used_at=old
    )
    svc.create_legal_hold(
        TENANT,
        scope={"payload_id": str(held_id)},
        reason_en="Litigation hold",
        reason_fr="Suspension légale",
    )

    with pytest.raises(ValueError, match="deletion blocked"):
        svc.request_deletion(TENANT, [held_id, due_id])

    with tenant_transaction(dsn, TENANT) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT deleted_at FROM encrypted_payload WHERE id = %s",
            (held_id,),
        )
        assert cur.fetchone()[0] is None

    result = svc.request_deletion(TENANT, [due_id])
    assert result.certificate_id is not None
    cert = svc.get_certificate(TENANT, result.certificate_id)
    assert cert is not None
    assert cert.status == DeletionCertificateStatus.PENDING
    assert cert.backup_expiry_note_en
    assert cert.backup_expiry_note_fr

    with tenant_transaction(dsn, TENANT) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT wrapped_key, destroyed_at FROM record_data_key WHERE payload_id = %s",
            (due_id,),
        )
        wrapped, destroyed_at = cur.fetchone()
        assert destroyed_at is not None
        assert wrapped == b"\x00" * len(wrapped)

    with tenant_transaction(dsn, TENANT) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE deletion_certificate
            SET key_destruction_scheduled_at = now() - interval '1 day'
            WHERE id = %s
            """,
            (result.certificate_id,),
        )

    finalized = svc.finalize_due_certificates(TENANT)
    assert any(
        c.id == result.certificate_id and c.status == DeletionCertificateStatus.FINAL
        for c in finalized
    )

    with tenant_transaction(dsn, TENANT) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT deleted_at FROM encrypted_payload WHERE id = %s",
            (held_id,),
        )
        assert cur.fetchone()[0] is None
