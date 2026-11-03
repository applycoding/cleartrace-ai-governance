from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_audit.verify import verify_tenant_chain
from cleartrace_db.session import tenant_transaction

from tests.trl5._helpers import TENANT_ALPHA, migrator_tenant_tx, pg_dsn

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    return pg_dsn()


def test_t23_audit_tamper_detection(dsn: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    worm_root = tmp_path_factory.mktemp("worm")
    ledger = AuditLedgerService(
        worm_root=worm_root,
        signer_key_path=tmp_path_factory.mktemp("keys") / "signer.key",
    )
    ledger.CHECKPOINT_EVENT_INTERVAL = 5

    _seed_events(dsn, ledger, count=12)

    with migrator_tenant_tx(TENANT_ALPHA) as conn:
        report = verify_tenant_chain(conn, tenant_id=TENANT_ALPHA, worm_root=worm_root)
    assert report.ok is True

    tamper_cases = ["edit", "delete", "reorder", "truncate"]
    detected = 0
    for case in tamper_cases:
        _seed_events(dsn, ledger, count=12)
        with migrator_tenant_tx(TENANT_ALPHA) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, prev_hash, event_hash, action, resource_type, resource_id, payload, occurred_at
                FROM audit_event WHERE tenant_id = %s ORDER BY occurred_at ASC, id ASC
                """,
                (TENANT_ALPHA,),
            )
            rows = cur.fetchall()
            if case == "edit" and rows:
                row = list(rows[2])
                row[3] = "tampered.action"
                cur.execute(
                    """
                    UPDATE audit_event SET action = %s WHERE id = %s
                    """,
                    (row[3], row[0]),
                )
            elif case == "delete" and rows:
                cur.execute("DELETE FROM audit_event WHERE id = %s", (rows[1][0],))
            elif case == "reorder" and len(rows) >= 3:
                a, b = rows[1], rows[2]
                cur.execute(
                    "UPDATE audit_event SET prev_hash = %s, event_hash = %s WHERE id = %s",
                    (b[1], b[2], a[0]),
                )
                cur.execute(
                    "UPDATE audit_event SET prev_hash = %s, event_hash = %s WHERE id = %s",
                    (a[1], a[2], b[0]),
                )
            elif case == "truncate" and rows:
                cur.execute(
                    """
                    DELETE FROM audit_event
                    WHERE tenant_id = %s AND id NOT IN (
                      SELECT id FROM audit_event WHERE tenant_id = %s ORDER BY occurred_at ASC LIMIT 3
                    )
                    """,
                    (TENANT_ALPHA, TENANT_ALPHA),
                )
            report = verify_tenant_chain(conn, tenant_id=TENANT_ALPHA, worm_root=worm_root)
            if not report.ok and report.findings:
                detected += 1

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "cleartrace_audit.cli",
            "--tenant-id",
            str(TENANT_ALPHA),
            "--dsn",
            dsn,
            "--worm-root",
            str(worm_root),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path.cwd()),
    )
    assert detected == 4
    assert cli.returncode != 0


def _seed_events(dsn: str, ledger: AuditLedgerService, *, count: int) -> None:
    _ = dsn
    with migrator_tenant_tx(TENANT_ALPHA) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM merkle_checkpoint WHERE tenant_id = %s", (TENANT_ALPHA,))
        cur.execute("DELETE FROM audit_pii WHERE tenant_id = %s", (TENANT_ALPHA,))
        cur.execute("DELETE FROM audit_event WHERE tenant_id = %s", (TENANT_ALPHA,))
    with tenant_transaction(dsn, TENANT_ALPHA) as conn:
        for i in range(count):
            ledger.append_event_tx(
                conn,
                tenant_id=TENANT_ALPHA,
                actor_id=None,
                action=f"seed.event.{i}",
                resource_type="test",
                resource_id=None,
                payload={"index": i},
            )
