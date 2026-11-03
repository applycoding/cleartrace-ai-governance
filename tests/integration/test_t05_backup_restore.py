from __future__ import annotations

import importlib.util
import os
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from cleartrace_core_api.data_policy.models import RetentionRuleBody
from cleartrace_core_api.data_policy.service import DataPolicyService

pytestmark = pytest.mark.trl5

TENANT = UUID("11111111-1111-7111-8111-111111111101")
EVIDENCE_RETENTION = RetentionRuleBody(
    artefact_class="evidence",
    configured_retention_days=30,
    statutory_floor_days=730,
)

ROOT = Path(__file__).resolve().parents[2]
RESTORE_PORT = int(os.environ.get("CLEARTRACE_T05_RESTORE_PORT", "5435"))
RESTORE_DB = "cleartrace_t05_restore"
RESTORE_DATA = ROOT / ".data" / "postgres-t05-restore"
ARTIFACT_DIR = ROOT / ".data" / "t05-restore"


def _backup_restore_module():
    path = ROOT / "tools" / "backup_restore.py"
    spec = importlib.util.spec_from_file_location("backup_restore", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("backup_restore module missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _app_dsn() -> str:
    return os.environ.get(
        "CLEARTRACE_TEST_DSN",
        "postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace",
    )


def _source_super_dsn() -> str:
    return os.environ.get(
        "CLEARTRACE_SUPER_DSN",
        "postgresql://cleartrace_super@127.0.0.1:5432/cleartrace",
    )


def _restore_super_dsn() -> str:
    return f"postgresql://cleartrace_super@127.0.0.1:{RESTORE_PORT}/{RESTORE_DB}"


def test_t05_pg_dump_restore_and_object_store() -> None:
    """Real pg_dump/pg_restore to a second cluster data directory (same VM, not a separate physical node)."""
    br = _backup_restore_module()
    app_dsn = _app_dsn()
    source_super = _source_super_dsn()
    svc = DataPolicyService(app_dsn)
    svc.upsert_retention(TENANT, [EVIDENCE_RETENTION])
    svc.store_encrypted_payload(
        TENANT,
        artefact_class="evidence",
        plaintext=b"backup-me-for-t05",
        last_used_at=datetime.now(tz=UTC) - timedelta(days=900),
    )

    source_objects = ARTIFACT_DIR / "source-objects"
    restore_objects = ARTIFACT_DIR / "restore-objects"
    dump_path = ARTIFACT_DIR / "cleartrace.dump"
    if ARTIFACT_DIR.exists():
        shutil.rmtree(ARTIFACT_DIR)
    source_objects.mkdir(parents=True)

    object_manifest = br.export_encrypted_object_store(source_super, source_objects)
    assert len(object_manifest) >= 1
    source_table_checksums = br.table_row_checksums(source_super)

    br.pg_dump_database(source_super, dump_path)

    br.ensure_postgres_cluster(RESTORE_DATA, RESTORE_PORT)
    restore_admin = f"postgresql://cleartrace_super@127.0.0.1:{RESTORE_PORT}/postgres"
    br.drop_and_create_database(restore_admin, RESTORE_DB)

    start = time.perf_counter()
    br.pg_restore_database(restore_admin, RESTORE_DB, dump_path)
    shutil.copytree(source_objects, restore_objects)
    restore_table_checksums = br.table_row_checksums(_restore_super_dsn())
    object_matched, object_total = br.verify_object_store(restore_objects, object_manifest)
    elapsed_s = time.perf_counter() - start

    table_matched, table_total = br.compare_table_checksums(
        source_table_checksums, restore_table_checksums
    )
    assert table_matched == table_total
    assert object_matched == object_total == len(object_manifest)
    assert elapsed_s >= 0.0

    print(
        "T-05 restore_seconds="
        f"{elapsed_s:.3f} table_checksums={table_matched}/{table_total} "
        f"objects={object_matched}/{object_total}"
    )
