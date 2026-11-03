from __future__ import annotations

from uuid import UUID

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient

from tests.trl5._helpers import pg_dsn
from tests.trl5.t06_matrix import build_matrix

pytestmark = [pytest.mark.integration, pytest.mark.trl5, pytest.mark.usefixtures("opa_server")]

TOKEN = "trl5-t06-matrix-token"
TENANTS = (
    UUID("11111111-1111-7111-8111-111111111101"),
    UUID("11111111-1111-7111-8111-111111111102"),
    UUID("11111111-1111-7111-8111-111111111103"),
)


def _sqlalchemy_url(dsn: str) -> str:
    return dsn.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture(scope="module")
def dsn() -> str:
    return pg_dsn()


@pytest.fixture(scope="module")
def client(dsn: str, tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    worm = tmp_path_factory.mktemp("worm")
    keys = tmp_path_factory.mktemp("keys")
    settings = Settings(
        dev_skip_auth=True,
        dev_auth_token=TOKEN,
        tenant_rate_limit_per_window=0,
        audit_worm_root=str(worm),
        audit_signer_key_path=str(keys / "signer.key"),
        database_url=_sqlalchemy_url(dsn),
    )
    return TestClient(create_app(settings))


def _headers(tenant_id: UUID, role: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    base = {
        "Authorization": f"Bearer {TOKEN}",
        "X-ClearTrace-Dev-Tenant": str(tenant_id),
        "X-ClearTrace-Dev-Roles": role,
    }
    if extra:
        base.update(extra)
    return base


def test_t06_full_auth_matrix_and_audit(dsn: str, client: TestClient) -> None:
    allowed, denied = build_matrix(target_each=600)
    assert len(allowed) == 600
    assert len(denied) == 600

    allowed_ok = 0
    forbidden_ok = 0
    for probe in allowed:
        kwargs: dict[str, object] = {"headers": _headers(probe.tenant_id, probe.role, probe.headers)}
        if probe.json_body is not None:
            kwargs["json"] = probe.json_body
        resp = client.request(probe.method, probe.path, **kwargs)
        if resp.status_code != 403:
            allowed_ok += 1
    for probe in denied:
        kwargs = {"headers": _headers(probe.tenant_id, probe.role, probe.headers)}
        if probe.json_body is not None:
            kwargs["json"] = probe.json_body
        resp = client.request(probe.method, probe.path, **kwargs)
        if resp.status_code == 403:
            forbidden_ok += 1

    assert allowed_ok == 600
    assert forbidden_ok == 600

    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM audit_event
            WHERE action = 'authz.denied' AND tenant_id = ANY(%s)
            """,
            (list(TENANTS),),
        )
        denial_rows = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*) FROM audit_event
            WHERE action = 'audit.read' AND tenant_id = ANY(%s)
            """,
            (list(TENANTS),),
        )
        read_rows = int(cur.fetchone()[0])
    assert denial_rows >= 600
    assert read_rows >= 1
