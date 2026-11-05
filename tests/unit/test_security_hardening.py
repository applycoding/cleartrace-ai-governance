"""Unit tests for the T-26 fixes: input guards, SSRF, traversal, tenant scoping, headers."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.auth.context import AuthContext
from cleartrace_core_api.config import Settings
from cleartrace_core_api.pagination import InvalidCursorError, decode_cursor, encode_cursor
from cleartrace_core_api.routers import assessments, connectors, reports
from cleartrace_notifier.webhook import WebhookURLError, validate_webhook_url
from fastapi.testclient import TestClient

TOKEN = "unit-test-hardening-token"
TENANT_A = "11111111-1111-7111-8111-111111111101"
TENANT_B = "22222222-2222-7222-8222-222222222202"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(dev_skip_auth=True, dev_auth_token=TOKEN)))


def _h(tenant: str = TENANT_A, **extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-ClearTrace-Dev-Tenant": tenant,
        "X-ClearTrace-Dev-Roles": "tenant_admin",
        **extra,
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/hook",
        "https://user:pw@example.com/hook",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.5/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/hook",
        "https:///nohost",
        "https://" + "a" * 64 + ".example.com/hook",
        "https://" + ".".join(["abcdefghij"] * 25) + ".com/hook",
        "https://bad..example.com/hook",
    ],
)
def test_webhook_urls_must_be_public_https(url: str) -> None:
    with pytest.raises(WebhookURLError):
        validate_webhook_url(url)


def test_public_https_webhook_url_is_accepted() -> None:
    validate_webhook_url("https://hooks.example.com/cleartrace")


def test_invalid_cursor_is_rejected() -> None:
    assert decode_cursor(encode_cursor(40)) == 40
    for bad in ("not-base64!!", encode_cursor(10**9)):
        with pytest.raises(InvalidCursorError):
            decode_cursor(bad)


def test_bad_cursor_is_a_422_not_a_500(client: TestClient) -> None:
    resp = client.get("/api/v1/systems?cursor=%%%", headers=_h())
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_nul_in_json_body_or_query_is_rejected(client: TestClient) -> None:
    body = client.post(
        "/api/v1/data-policy/legal-holds",
        headers=_h(),
        json={"scope": {}, "reason_en": "a\u0000b", "reason_fr": "x"},
    )
    assert body.status_code == 422
    query = client.get("/api/v1/systems?cursor=%00", headers=_h())
    assert query.status_code == 422


def test_nul_in_evidence_form_fields_is_422_not_500(client: TestClient) -> None:
    """Multipart titles with NUL must not reach Postgres (ST101 on POST /evidence)."""
    resp = client.post(
        "/api/v1/evidence",
        headers=_h(),
        data={
            "artefact_class": "approval",
            "title_en": "Evidence artefact",
            "title_fr": "bad\x00title",
        },
        files={"file": ("file.png", b"PNGDATA", "image/png")},
    )
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_unknown_evidence_form_field_is_422(client: TestClient) -> None:
    """additionalProperties:false on evidence multipart must be enforced (ST201)."""
    resp = client.post(
        "/api/v1/evidence",
        headers=_h(),
        data={
            "artefact_class": "approval",
            "title_en": "Evidence artefact",
            "title_fr": "Artefact de preuve",
            "x-schemathesis-unknown-property": "42",
        },
        files={"file": ("file.png", b"PNGDATA", "image/png")},
    )
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")

def test_security_headers_on_api_responses(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "max-age=" in resp.headers["Strict-Transport-Security"]
    assert resp.headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert resp.headers["Cache-Control"] == "no-store"


def test_405_lists_every_documented_method(client: TestClient) -> None:
    resp = client.request("DELETE", "/api/v1/baselines", headers=_h())
    assert resp.status_code == 405
    assert {"GET", "POST"} <= {m.strip() for m in resp.headers["Allow"].split(",")}


def test_post_to_get_only_system_path_is_405_not_400(client: TestClient) -> None:
    resp = client.post(f"/api/v1/systems/{uuid4()}", headers=_h(), json={})
    assert resp.status_code == 405


def test_bad_token_gets_a_generic_401() -> None:
    app = create_app(Settings(dev_skip_auth=False, keycloak_jwks_url="http://127.0.0.1:9/certs"))
    resp = TestClient(app).get("/api/v1/systems", headers={"Authorization": "Bearer junk"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Bearer token is invalid or expired"


@pytest.mark.parametrize("name", ["../../pyproject", "..%2F..%2Fetc", "MLflow", "a/b"])
def test_connector_manifest_name_cannot_escape(client: TestClient, name: str) -> None:
    resp = client.post("/api/v1/connectors", headers=_h(), json={"manifest_name": name})
    assert resp.status_code in {404, 422}


def test_connector_fixture_name_cannot_escape(client: TestClient) -> None:
    cid = str(uuid4())
    connectors._installed[cid] = {"tenant_id": TENANT_A, "name": "mlflow", "version": "1"}
    try:
        resp = client.post(
            f"/api/v1/connectors/{cid}:run",
            headers=_h(),
            json={"system_id": str(uuid4()), "fixture_name": "../../../pyproject"},
        )
        assert resp.status_code == 422
    finally:
        connectors._installed.pop(cid, None)


def test_in_memory_records_are_tenant_scoped(client: TestClient) -> None:
    report_id, job_id, conn_id = str(uuid4()), str(uuid4()), str(uuid4())
    reports._artifacts[report_id] = {
        "tenant_id": TENANT_A,
        "content_type": "application/json",
        "body": b"{}",
        "filename": "r.json",
    }
    assessments._jobs[job_id] = {
        "tenant_id": TENANT_A,
        "id": job_id,
        "status": "completed",
        "finding_id": None,
        "outcome_state": None,
        "reason_code": None,
        "certainty_index": None,
    }
    connectors._installed[conn_id] = {"tenant_id": TENANT_A, "name": "mlflow", "version": "1"}
    try:
        assert client.get(f"/api/v1/reports/{report_id}", headers=_h(TENANT_A)).status_code == 200
        assert client.get(f"/api/v1/reports/{report_id}", headers=_h(TENANT_B)).status_code == 404
        own = client.get(f"/api/v1/reports/{report_id}", headers=_h(TENANT_A))
        assert own.headers["Content-Disposition"].startswith("attachment;")
        assert client.get(f"/api/v1/assessments/{job_id}", headers=_h(TENANT_B)).status_code == 404
        listed_b = client.get("/api/v1/connectors", headers=_h(TENANT_B)).json()["items"]
        assert conn_id not in {item["id"] for item in listed_b}
        listed_a = client.get("/api/v1/connectors", headers=_h(TENANT_A)).json()["items"]
        assert conn_id in {item["id"] for item in listed_a}
    finally:
        reports._artifacts.pop(report_id, None)
        assessments._jobs.pop(job_id, None)
        connectors._installed.pop(conn_id, None)


def test_actor_id_is_stable_for_non_uuid_subjects() -> None:
    tenant = UUID(TENANT_A)
    ctx = AuthContext(
        subject="alice@example", tenant_id=tenant, roles=frozenset(), org_unit=None, raw_claims={}
    )
    again = AuthContext(
        subject="alice@example", tenant_id=tenant, roles=frozenset(), org_unit=None, raw_claims={}
    )
    assert ctx.actor_id == again.actor_id
    uuid_subject = str(uuid4())
    direct = AuthContext(
        subject=uuid_subject, tenant_id=tenant, roles=frozenset(), org_unit=None, raw_claims={}
    )
    assert str(direct.actor_id) == uuid_subject


def test_fixture_loader_stays_inside_the_fixtures_folder() -> None:
    from cleartrace_connectors.builtin import load_mlflow_fixture

    assert load_mlflow_fixture("default")
    with pytest.raises(FileNotFoundError):
        load_mlflow_fixture("../../pyproject")


@pytest.mark.parametrize("key", ["has space", "x" * 129, "tab\there"])
def test_idempotency_key_must_be_visible_ascii(client: TestClient, key: str) -> None:
    resp = client.post(
        "/api/v1/systems",
        headers={**_h(), "Idempotency-Key": key},
        json={},
    )
    assert resp.status_code == 400
    assert resp.json()["title"] == "Invalid idempotency key"


def test_idempotency_key_schema_matches_the_middleware(client: TestClient) -> None:
    op = client.app.openapi()["paths"]["/api/v1/systems"]["post"]  # type: ignore[attr-defined]
    (param,) = [p for p in op["parameters"] if p["name"] == "Idempotency-Key"]
    assert param["required"] is True
    assert param["schema"]["pattern"] == "^[!-~]{1,128}$"


def test_delivery_to_an_unresolvable_host_is_a_failed_attempt_not_a_crash() -> None:
    import asyncio

    from cleartrace_notifier.webhook import HttpxWebhookTransport

    async def attempt() -> tuple[int, str]:
        return await HttpxWebhookTransport().post(
            "https://" + "a" * 64 + ".example.com/hook", {}, b"{}"
        )

    code, text = asyncio.run(attempt())
    assert code == 0
    assert text.startswith("blocked:")


def test_malformed_register_csv_is_422_not_500(client: TestClient) -> None:
    # The CI run 41728473464 payload: a bare CR in an unquoted field used to raise csv.Error.
    resp = client.post(
        "/api/v1/register/import/gc-ai-register",
        headers=_h(),
        json={"csv_content": "*\u0005\u00eb\u0015\r\u0087\u00b8X"},
    )
    assert resp.status_code == 200
    too_big = client.post(
        "/api/v1/register/import/gc-ai-register",
        headers=_h(),
        json={"csv_content": "a\n\"" + "x" * 140_000 + "\"\n"},
    )
    assert too_big.status_code == 422


def test_imported_register_systems_are_tenant_scoped(client: TestClient) -> None:
    from cleartrace_register.api import router as register_router

    csv_text = (
        "Nom du système d'IA / Name of the AI system,État / Status\nScoped System,Active\n"
    )
    resp = client.post(
        "/api/v1/register/import/gc-ai-register",
        headers=_h(TENANT_A),
        json={"csv_content": csv_text},
    )
    assert resp.status_code == 200
    (system_id,) = [s for s, t in register_router._system_tenant.items() if t == TENANT_A][-1:]
    path = f"/api/v1/register/systems/{system_id}"
    assert client.get(path, headers=_h(TENANT_A)).status_code == 200
    assert client.get(path, headers=_h(TENANT_B)).status_code == 404


def test_docs_page_runs_without_inline_script_or_cdn(client: TestClient) -> None:
    import re

    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200
    csp = resp.headers["Content-Security-Policy"]
    assert "'unsafe-inline'" not in csp
    assert "http" not in csp
    assert "script-src 'self';" in csp
    html = resp.text
    assert "http://" not in html and "https://" not in html
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "inline script found"
    for src in re.findall(r'(?:src|href)="([^"]+)"', html):
        asset = client.get(src)
        assert asset.status_code == 200, src


def test_only_listed_docs_assets_are_public(client: TestClient) -> None:
    assert client.get("/api/v1/swagger-ui/NOTICE").status_code == 401


def test_unknown_but_well_formed_cursor_is_empty_page(client: TestClient) -> None:
    # Pattern-valid cursor this API did not issue → empty page (ST202 accepts 2xx).
    resp = client.get("/api/v1/systems?cursor=YWJjZGVmZ2hpams=", headers=_h())
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None


def test_webhook_url_rejects_ports_above_65535() -> None:
    from cleartrace_notifier.router import WebhookCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WebhookCreate(url="https://hooks.example.com:79495/path", secret="s" * 16)
    ok = WebhookCreate(url="https://hooks.example.com:8443/path", secret="s" * 16)
    assert ok.url.endswith(":8443/path")


def test_audit_event_hash_is_grouped_for_list_responses() -> None:
    from cleartrace_core_api.routers.audit import _grouped_hash

    assert _grouped_hash("0" * 64) == " ".join(["0" * 8] * 8)
    assert "587215541035809" not in _grouped_hash("5872155410358090" + "ab" * 24)
