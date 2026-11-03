from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import jwt
import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.auth import middleware as auth_middleware
from cleartrace_core_api.auth.middleware import decode_bearer_token, is_dev_token
from cleartrace_core_api.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request
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


OTHER_TENANT = "22222222-2222-7222-8222-222222222202"
JWT_TENANT = "33333333-3333-7333-8333-333333333303"


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw})


def test_dev_tenant_header_applies_only_with_dev_token() -> None:
    settings = Settings(dev_skip_auth=True, dev_auth_token=TOKEN)
    ctx = asyncio.run(
        decode_bearer_token(settings, TOKEN, _request({"X-ClearTrace-Dev-Tenant": OTHER_TENANT}))
    )
    assert str(ctx.tenant_id) == OTHER_TENANT


def test_dev_tenant_header_rejected_when_flag_off() -> None:
    settings = Settings(
        dev_skip_auth=False, dev_auth_token=TOKEN, keycloak_jwks_url=UNREACHABLE_JWKS
    )
    assert _status(settings, TOKEN, {"X-ClearTrace-Dev-Tenant": OTHER_TENANT}) == 401
    settings = Settings(dev_skip_auth=True, dev_auth_token="", keycloak_jwks_url=UNREACHABLE_JWKS)
    assert _status(settings, "", {"X-ClearTrace-Dev-Tenant": OTHER_TENANT}) == 401


def test_dev_tenant_header_ignored_for_real_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk["kid"] = "unit"

    async def _keys(_url: str) -> dict[str, object]:
        return {"keys": [jwk]}

    monkeypatch.setattr(auth_middleware._jwks_cache, "get_keys", _keys)
    settings = Settings(dev_skip_auth=True, dev_auth_token=TOKEN)
    claims = {
        "sub": "real-user",
        "tenant_id": JWT_TENANT,
        "aud": settings.keycloak_audience,
        "iss": settings.keycloak_issuer,
        "exp": int(time.time()) + 300,
    }
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "unit"})
    ctx = asyncio.run(
        decode_bearer_token(settings, token, _request({"X-ClearTrace-Dev-Tenant": OTHER_TENANT}))
    )
    assert str(ctx.tenant_id) == JWT_TENANT
