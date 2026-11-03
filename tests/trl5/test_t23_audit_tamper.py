from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_audit.verify import verify_tenant_chain
from cleartrace_db.session import tenant_transaction

from tests.trl5._helpers import TENANT_ALPHA, migrator_dsn, migrator_tenant_tx, pg_dsn

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def dsn() -> str:
    return pg_dsn()


# Where each tamper must be located (row index in occurred_at, id order).
EXPECTED_LOCATION = {
    "edit": ("edited_event", 2),
    "delete": ("broken_chain", 1),
    "reorder": ("broken_chain", 1),
    "truncate": ("truncation", 3),
}


def _expected_window(cur, tenant_id) -> int:
    """Live rows not yet anchored by any checkpoint, straight from the tables."""
    cur.execute("SELECT COUNT(*) FROM audit_event WHERE tenant_id = %s", (tenant_id,))
    live = int(cur.fetchone()[0])
    cur.execute(
        "SELECT COALESCE(MAX(tree_size), 0) FROM merkle_checkpoint WHERE tenant_id = %s",
        (tenant_id,),
    )
    anchored = int(cur.fetchone()[0])
    return max(0, live - anchored)


def test_t23_audit_tamper_detection(
    dsn: str, tmp_path_factory: pytest.TempPathFactory, record_property
) -> None:
    worm_root = tmp_path_factory.mktemp("worm")
    ledger = AuditLedgerService(
        worm_root=worm_root,
        signer_key_path=tmp_path_factory.mktemp("keys") / "signer.key",
    )
    ledger.CHECKPOINT_EVENT_INTERVAL = 5

    _seed_events(dsn, ledger, count=12)

    with migrator_tenant_tx(TENANT_ALPHA) as conn, conn.cursor() as cur:
        report = verify_tenant_chain(conn, tenant_id=TENANT_ALPHA, worm_root=worm_root)
        clean_window = _expected_window(cur, TENANT_ALPHA)
    assert report.ok is True
    assert report.checkpoint_count >= 1
    assert clean_window > 0, "fixture must leave rows after the last checkpoint"
    assert report.exposure_window_events == clean_window
    assert report.exposure_window_start is not None
    assert report.exposure_window_seconds >= 0

    detected = 0
    located = 0
    for case, (kind, row) in EXPECTED_LOCATION.items():
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
            assert len(rows) == 12
            if case == "edit":
                cur.execute(
                    "UPDATE audit_event SET action = %s WHERE id = %s",
                    ("tampered.action", rows[2][0]),
                )
            elif case == "delete":
                cur.execute("DELETE FROM audit_event WHERE id = %s", (rows[1][0],))
            elif case == "reorder":
                a, b = rows[1], rows[2]
                cur.execute(
                    "UPDATE audit_event SET prev_hash = %s, event_hash = %s WHERE id = %s",
                    (b[1], b[2], a[0]),
                )
                cur.execute(
                    "UPDATE audit_event SET prev_hash = %s, event_hash = %s WHERE id = %s",
                    (a[1], a[2], b[0]),
                )
            elif case == "truncate":
                cur.execute(
                    """
                    DELETE FROM audit_event
                    WHERE tenant_id = %s AND id NOT IN (
                      SELECT id FROM audit_event WHERE tenant_id = %s
                      ORDER BY occurred_at ASC, id ASC LIMIT 3
                    )
                    """,
                    (TENANT_ALPHA, TENANT_ALPHA),
                )
            report = verify_tenant_chain(conn, tenant_id=TENANT_ALPHA, worm_root=worm_root)
            window = _expected_window(cur, TENANT_ALPHA)
        assert not report.ok and report.findings, f"{case} not detected"
        detected += 1
        assert any(f.kind == kind and f.row_index == row for f in report.findings), (
            f"{case} not located at {kind} row {row}: {report.findings}"
        )
        located += 1
        assert report.exposure_window_events == window, case

    record_property("t23_tamper_cases_detected", detected)
    record_property("t23_tamper_cases_located", located)
    record_property("t23_clean_exposure_window_events", clean_window)
    assert detected == 4 and located == 4

    # The operator CLI (run with the migrator DSN, as an operator would) shows the
    # same result for the last (truncated) state. Exit 1 means tampering found.
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "cleartrace_audit.cli",
            "--tenant-id",
            str(TENANT_ALPHA),
            "--dsn",
            migrator_dsn(),
            "--worm-root",
            str(worm_root),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path.cwd()),
    )
    assert cli.returncode == 1, cli.stderr
    shown = json.loads(cli.stdout)
    assert shown["ok"] is False
    assert shown["exposure_window_events"] == window
    assert "exposure_window_seconds" in shown and "exposure_window_start" in shown
    assert any(f["kind"] == "truncation" and f["row_index"] == 3 for f in shown["findings"])


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
