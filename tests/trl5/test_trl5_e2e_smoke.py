from __future__ import annotations

import io
import os

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from cleartrace_risk.catalogue import catalogue_by_code
from fastapi.testclient import TestClient

from tests.trl5._helpers import (
    TENANT_ALPHA,
    ensure_principal,
    ensure_system_with_owner,
    pg_dsn,
)

pytestmark = [pytest.mark.integration, pytest.mark.trl5]

TOKEN = "trl5-e2e-smoke-token"


def _headers(role: str, principal_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-ClearTrace-Dev-Roles": role,
        "X-ClearTrace-Dev-Principal": principal_id,
        "Accept-Language": "en-CA",
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
        dev_tenant_id=TENANT_ALPHA,
        audit_worm_root=str(worm),
        audit_signer_key_path=str(keys / "signer.key"),
        database_url=os.environ.get(
            "CLEARTRACE_DATABASE_URL",
            "postgresql+psycopg://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace",
        ),
    )
    return TestClient(create_app(settings))


def test_trl5_e2e_smoke_http_journey(client: TestClient, dsn: str) -> None:
    owner_id = ensure_principal(
        dsn, tenant_id=TENANT_ALPHA, role_code="system_owner", email_suffix="e2e-owner"
    )
    reviewer_id = ensure_principal(
        dsn,
        tenant_id=TENANT_ALPHA,
        role_code="oversight_reviewer",
        email_suffix="e2e-reviewer",
    )
    system_id = ensure_system_with_owner(
        dsn,
        tenant_id=TENANT_ALPHA,
        owner_principal_id=owner_id,
        system_key="SYS-E2E",
    )

    reg = client.post(
        "/api/v1/systems",
        headers=_headers("system_owner", str(owner_id)),
        json={
            "system_key": "SYS-E2E-API",
            "name_en": "E2E system",
            "name_fr": "Système E2E",
        },
    )
    assert reg.status_code == 201
    api_system_id = reg.json()["id"]

    assess = client.post(
        "/api/v1/assessments",
        headers=_headers("assessor", str(owner_id)),
        json={"ai_system_id": api_system_id, "pack_slug": "dadm"},
    )
    assert assess.status_code == 202
    finding_id = assess.json()["finding_id"]
    assert finding_id

    finding = client.get(
        f"/api/v1/findings/{finding_id}",
        headers=_headers("oversight_reviewer", str(reviewer_id)),
    )
    assert finding.status_code == 200
    etag = finding.json()["etag"]

    review = client.post(
        f"/api/v1/findings/{finding_id}/actions",
        headers={**_headers("oversight_reviewer", str(reviewer_id)), "If-Match": etag},
        json={
            "action": "validate",
            "rationale_en": "E2E validation",
            "rationale_fr": "Validation E2E",
        },
    )
    assert review.status_code == 200

    evidence = client.post(
        "/api/v1/evidence",
        headers=_headers("system_owner", str(owner_id)),
        data={"artefact_class": "assessment_records"},
        files={"file": ("proof.txt", io.BytesIO(b"evidence"), "text/plain")},
    )
    assert evidence.status_code == 201

    metric = list(catalogue_by_code().keys())[0]
    breach_value = catalogue_by_code()[metric].default_breach * 2
    obs = client.post(
        "/api/v1/observations",
        headers=_headers("assessor", str(owner_id)),
        json={
            "observations": [
                {
                    "metric_code": metric,
                    "ai_system_id": str(system_id),
                    "value": breach_value,
                    "binding": True,
                }
            ]
        },
    )
    assert obs.status_code == 201
    assert obs.json()["results"][0]["alert_raised"] is True

    alert = client.post(
        "/api/v1/notifications:dispatch",
        headers=_headers("tenant_admin", str(owner_id)),
        json={
            "alert_type": "binding_breach",
            "system_id": str(system_id),
            "reason": "e2e",
            "title_en": "Breach",
            "title_fr": "Dépassement",
        },
    )
    assert alert.status_code == 200

    verify = client.post(
        "/api/v1/audit:verify",
        headers=_headers("auditor", str(reviewer_id)),
    )
    assert verify.status_code == 200
    assert "ok" in verify.json()

    events = client.get(
        "/api/v1/audit/events",
        headers=_headers("auditor", str(reviewer_id)),
    )
    assert events.status_code == 200
    assert events.json()["tree_size"] >= 1
