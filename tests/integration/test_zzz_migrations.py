from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

import psycopg
import pytest


def _reset_tenant_data(url: str) -> None:
    dsn = url.replace("postgresql+psycopg", "postgresql", 1)
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
                TRUNCATE processed_event_ids, outbox, audit_event, ai_system_version,
                  ai_system, role_assignment, principal, org_unit, tenant_cell_binding
                RESTART IDENTITY CASCADE
                """
        )


@pytest.mark.integration
def test_migrations_upgrade_and_downgrade() -> None:
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    pg_port = os.environ.get("CLEARTRACE_PGPORT", "55432")
    env["CLEARTRACE_DATABASE_URL"] = env.get(
        "CLEARTRACE_DATABASE_URL",
        f"postgresql+psycopg://cleartrace_super@127.0.0.1:{pg_port}/cleartrace",
    )
    _reset_tenant_data(env["CLEARTRACE_DATABASE_URL"])
    alembic = ["uv", "run", "alembic", "-c", "alembic.ini"]
    subprocess.check_call(alembic + ["downgrade", "base"], cwd=root / "db", env=env)
    subprocess.check_call(alembic + ["upgrade", "head"], cwd=root / "db", env=env)
    pidfile = root / ".data" / "pgbouncer.pid"
    if pidfile.exists():
        os.kill(int(pidfile.read_text().strip()), signal.SIGHUP)
