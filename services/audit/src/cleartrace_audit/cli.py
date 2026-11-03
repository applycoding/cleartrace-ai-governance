from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

import psycopg
from cleartrace_db.session import tenant_transaction

from cleartrace_audit.verify import verify_tenant_chain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify ClearTrace audit hash chain and WORM checkpoints."
    )
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--dsn", default=os.environ.get("CLEARTRACE_TEST_DSN", ""))
    parser.add_argument(
        "--worm-root",
        default=os.environ.get("CLEARTRACE_WORM_ROOT", ".data/worm-audit"),
    )
    args = parser.parse_args(argv)
    if not args.dsn:
        print("Database DSN required (--dsn or CLEARTRACE_TEST_DSN)", file=sys.stderr)
        return 2
    tenant_id = UUID(args.tenant_id)
    worm_root = Path(args.worm_root)
    try:
        with tenant_transaction(args.dsn, tenant_id, role="cleartrace_migrator") as conn:
            report = verify_tenant_chain(conn, tenant_id=tenant_id, worm_root=worm_root)
    except psycopg.Error as exc:
        # Exit 2, not 1: a connection or privilege error must never read as tampering.
        print(f"Could not read the audit ledger: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_report_dict(report), indent=2, sort_keys=True))
    return 0 if report.ok else 1


def _report_dict(report: object) -> dict[str, object]:
    from cleartrace_audit.verify import VerificationReport

    if not isinstance(report, VerificationReport):
        return {"ok": False}
    return {
        "tenant_id": str(report.tenant_id),
        "ok": report.ok,
        "tree_size": report.tree_size,
        "checkpoint_count": report.checkpoint_count,
        "exposure_window_events": report.exposure_window_events,
        "exposure_window_seconds": report.exposure_window_seconds,
        "exposure_window_start": report.exposure_window_start,
        "findings": [
            {
                "kind": f.kind,
                "row_index": f.row_index,
                "checkpoint_index": f.checkpoint_index,
                "detail": f.detail,
            }
            for f in report.findings
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
