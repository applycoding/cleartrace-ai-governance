from __future__ import annotations

import os
from pathlib import Path

import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.auth.middleware import is_dev_token
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "unit-test-dev-guard-token"
HELM = ROOT / "deploy" / "helm" / "cleartrace"
UNREACHABLE_JWKS = "http://127.0.0.1:9/certs"


def _status(settings: Settings, token: str, extra: dict[str, str] | None = None) -> int:
    client = TestClient(create_app(settings))
    headers = {"Authorization": f"Bearer {token}", **(extra or {})}
    return client.get("/api/v1/systems", headers=headers).status_code


def test_dev_auth_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("CLEARTRACE_DEV_"):
            monkeypatch.delenv(key)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.dev_skip_auth is False
    assert settings.dev_auth_token == ""


def test_dev_auth_needs_both_flag_and_token() -> None:
    assert is_dev_token(Settings(dev_skip_auth=True, dev_auth_token=TOKEN), TOKEN)
    assert not is_dev_token(Settings(dev_skip_auth=False, dev_auth_token=TOKEN), TOKEN)
    assert not is_dev_token(Settings(dev_skip_auth=True, dev_auth_token=""), "")
    assert not is_dev_token(Settings(dev_skip_auth=True, dev_auth_token=TOKEN), "other")


def test_dev_token_rejected_when_flag_off() -> None:
    settings = Settings(
        dev_skip_auth=False, dev_auth_token=TOKEN, keycloak_jwks_url=UNREACHABLE_JWKS
    )
    assert _status(settings, TOKEN) == 401


def test_dev_flag_without_token_rejects_everything() -> None:
    settings = Settings(dev_skip_auth=True, dev_auth_token="", keycloak_jwks_url=UNREACHABLE_JWKS)
    assert _status(settings, "", {"X-ClearTrace-Dev-Roles": "tenant_admin"}) == 401
    assert _status(settings, "anything", {"X-ClearTrace-Dev-Roles": "tenant_admin"}) == 401


def test_helm_cannot_enable_dev_auth() -> None:
    template = (HELM / "templates/deployment.yaml").read_text(encoding="utf-8")
    assert '- name: CLEARTRACE_DEV_SKIP_AUTH\n              value: "false"' in template
    assert '- name: CLEARTRACE_DEV_AUTH_TOKEN\n              value: ""' in template
    values = (HELM / "values.yaml").read_text(encoding="utf-8").lower()
    assert "dev_skip_auth" not in values
    assert "devskipauth" not in values
    assert "dev_auth" not in values
    assert "extraenv" not in values
