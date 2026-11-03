from __future__ import annotations

from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient


def test_health_unauthenticated() -> None:
    app = create_app(Settings(dev_skip_auth=True))
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_problem_json_on_missing_token() -> None:
    app = create_app(Settings(dev_skip_auth=False))
    client = TestClient(app)
    resp = client.get("/api/v1/admin/ping")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_dev_auth_and_language_header() -> None:
    app = create_app(Settings(dev_skip_auth=True))
    client = TestClient(app)
    resp = client.get(
        "/api/v1/systems",
        headers={"Authorization": "Bearer dev", "Accept-Language": "fr-CA"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("Content-Language") == "fr-CA"
