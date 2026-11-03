from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient

from tests.trl5._helpers import ensure_principal, ensure_system_with_owner, pg_dsn

pytestmark = [pytest.mark.integration, pytest.mark.trl5, pytest.mark.usefixtures("opa_server")]

TOKEN = "trl5-t21-multi-tenant-token"

TENANT_ALPHA = UUID("11111111-1111-7111-8111-111111111101")
TENANT_BETA = UUID("11111111-1111-7111-8111-111111111102")
TENANT_GAMMA = UUID("11111111-1111-7111-8111-111111111103")

TENANT_CONFIG = (
    (
        TENANT_ALPHA,
        "dadm",
        "CA-DADM-APP-C-03",
        {"planned_production_use": True, "impact_level": 3},
        [],
    ),
    (
        TENANT_BETA,
        "aia",
        "CA-AIA-SCORE-01",
        {"planned_production_use": True},
        [{"type": "aia_record", "authorized_submitter": True, "valid_until": "2099-01-01"}],
    ),
    (
        TENANT_GAMMA,
        "psd",
        "CA-PSD-4-1-28",
        {"planned_production_use": True},
        [
            {
                "type": "design_by_default_record",
                "authorized_submitter": True,
                "valid_until": "2099-01-01",
            }
        ],
    ),
)


def _headers(tenant_id: UUID, principal_id: str, role: str = "assessor") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-ClearTrace-Dev-Tenant": str(tenant_id),
        "X-ClearTrace-Dev-Roles": role,
        "X-ClearTrace-Dev-Principal": principal_id,
    }


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
        tenant_rate_limit_per_window=8,
        tenant_rate_limit_window_seconds=60,
        audit_worm_root=str(worm),
        audit_signer_key_path=str(keys / "signer.key"),
        database_url=os.environ.get(
            "CLEARTRACE_DATABASE_URL",
            "postgresql+psycopg://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace",
        ),
    )
    return TestClient(create_app(settings))


@pytest.fixture(scope="module")
def tenant_context(dsn: str) -> dict[UUID, dict[str, str]]:
    ctx: dict[UUID, dict[str, str]] = {}
    for tenant_id, _pack, _control, _profile, _evidence in TENANT_CONFIG:
        owner = ensure_principal(
            dsn,
            tenant_id=tenant_id,
            role_code="system_owner",
            email_suffix=f"t21-{str(tenant_id)[-3:]}",
        )
        system_id = ensure_system_with_owner(
            dsn,
            tenant_id=tenant_id,
            owner_principal_id=owner,
            system_key=f"SYS-T21-{str(tenant_id)[-3:]}",
        )
        ctx[tenant_id] = {"owner": str(owner), "system_id": str(system_id)}
    return ctx


def test_t21_three_tenants_isolated_policies_and_rate_limits(
    client: TestClient,
    tenant_context: dict[UUID, dict[str, str]],
) -> None:
    """Blueprint T-21: each tenant sees only its own results; per-tenant rate limits hold."""
    findings_by_tenant: dict[UUID, str] = {}

    def run_assessment(tenant_id: UUID, pack: str, control: str, profile: dict, evidence: list) -> tuple[UUID, int, dict]:
        meta = tenant_context[tenant_id]
        resp = client.post(
            "/api/v1/assessments",
            headers=_headers(tenant_id, meta["owner"]),
            json={
                "ai_system_id": meta["system_id"],
                "pack_slug": pack,
                "control_key": control,
                "system_profile": profile,
                "evidence": evidence,
            },
        )
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        return tenant_id, resp.status_code, body

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(run_assessment, tenant_id, pack, control, dict(profile), list(evidence))
            for tenant_id, pack, control, profile, evidence in TENANT_CONFIG
        ]
        results = [f.result() for f in as_completed(futures)]

    for tenant_id, status, body in results:
        assert status == 202, body
        findings_by_tenant[tenant_id] = body["finding_id"]
        assert body.get("outcome_state")

    for tenant_id, pack, _control, _profile, _evidence in TENANT_CONFIG:
        meta = tenant_context[tenant_id]
        own = findings_by_tenant[tenant_id]
        ok = client.get(
            f"/api/v1/findings/{own}",
            headers=_headers(tenant_id, meta["owner"], "oversight_reviewer"),
        )
        assert ok.status_code == 200
        for other_tid, foreign_id in findings_by_tenant.items():
            if other_tid == tenant_id:
                continue
            blocked = client.get(
                f"/api/v1/findings/{foreign_id}",
                headers=_headers(tenant_id, meta["owner"], "oversight_reviewer"),
            )
            assert blocked.status_code == 404
        assert pack

    tenant_id, pack, control, profile, evidence = TENANT_CONFIG[0]
    meta = tenant_context[tenant_id]
    burst_codes: list[int] = []
    for _ in range(12):
        resp = client.post(
            "/api/v1/assessments",
            headers=_headers(tenant_id, meta["owner"]),
            json={
                "ai_system_id": meta["system_id"],
                "pack_slug": pack,
                "control_key": control,
                "system_profile": profile,
                "evidence": evidence,
            },
        )
        burst_codes.append(resp.status_code)
    assert 429 in burst_codes, burst_codes
