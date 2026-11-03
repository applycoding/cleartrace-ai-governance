from __future__ import annotations

import os
from uuid import UUID

import pytest
from cleartrace_connectors.nats_js import default_nats_url, ensure_stream

TENANT_TRL = UUID("11111111-1111-7111-8111-111111111101")


def _pgbouncer_dsn() -> str:
    host = os.environ.get("CLEARTRACE_PGBOUNCER_HOST", "127.0.0.1")
    port = os.environ.get("CLEARTRACE_PGBOUNCER_PORT", "6432")
    return f"postgresql://cleartrace_app:cleartrace_app@{host}:{port}/cleartrace"


@pytest.fixture(scope="module")
def trl_dsn() -> str:
    return os.environ.get("CLEARTRACE_TEST_DSN") or _pgbouncer_dsn()


@pytest.fixture(scope="module")
def trl_tenant_id() -> UUID:
    return TENANT_TRL


@pytest.fixture(scope="module")
def nats_url() -> str:
    """NATS JetStream URL (CLEARTRACE_NATS_URL; CI starts NATS through Compose)."""
    import asyncio

    url = default_nats_url()
    asyncio.run(ensure_stream(url))
    return url


def count_processed_events(dsn: str) -> int:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SET ROLE cleartrace_app")
        cur.execute("SELECT count(*) FROM processed_event_ids")
        row = cur.fetchone()
        return int(row[0]) if row else 0
