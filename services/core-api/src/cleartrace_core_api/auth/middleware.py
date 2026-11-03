from __future__ import annotations

import secrets
import time
from typing import Any
from uuid import UUID

import httpx
import jwt
from cleartrace_core_api.auth.cedar_engine import CedarAuthorizer
from cleartrace_core_api.auth.context import AuthContext
from cleartrace_core_api.auth.route_actions import action_for_request
from cleartrace_core_api.config import Settings
from cleartrace_core_api.deps import get_audit_ledger
from cleartrace_core_api.errors import problem_response
from cleartrace_db.session import tenant_transaction
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class _JwksCache:
    def __init__(self) -> None:
        self._keys: dict[str, Any] | None = None
        self._fetched_at: float = 0.0

    async def get_keys(self, url: str) -> dict[str, Any]:
        if self._keys and time.time() - self._fetched_at < 300:
            return self._keys
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._keys = resp.json()
            self._fetched_at = time.time()
            return self._keys


_jwks_cache = _JwksCache()


def _tenant_from_claims(claims: dict[str, Any]) -> UUID:
    raw = claims.get("tenant_id") or claims.get("cleartrace_tenant_id")
    if not raw:
        raise ValueError("tenant_id missing from token")
    return UUID(str(raw))


def _roles_from_claims(claims: dict[str, Any]) -> frozenset[str]:
    realm = claims.get("realm_access") or {}
    roles = set(realm.get("roles") or [])
    resource = claims.get("resource_access") or {}
    for entry in resource.values():
        roles.update(entry.get("roles") or [])
    extra = claims.get("cleartrace_roles") or []
    roles.update(extra)
    return frozenset(str(r) for r in roles)


def _dev_roles_from_request(request: Request) -> frozenset[str] | None:
    raw = request.headers.get("X-ClearTrace-Dev-Roles", "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return frozenset(parts) if parts else None


async def decode_bearer_token(settings: Settings, token: str) -> AuthContext:
    if (
        settings.dev_skip_auth
        and settings.dev_auth_token
        and secrets.compare_digest(token, settings.dev_auth_token)
    ):
        return AuthContext(
            subject="dev-user",
            tenant_id=settings.dev_tenant_id,
            roles=frozenset({"tenant_admin"}),
            org_unit=None,
            raw_claims={},
        )
    jwks = await _jwks_cache.get_keys(settings.keycloak_jwks_url)
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key_data is None:
        raise jwt.InvalidTokenError("unknown signing key")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
    claims = jwt.decode(
        token,
        public_key,  # type: ignore[arg-type]
        algorithms=["RS256"],
        audience=settings.keycloak_audience,
        issuer=settings.keycloak_issuer,
    )
    tenant_id = _tenant_from_claims(claims)
    roles = _roles_from_claims(claims)
    return AuthContext(
        subject=str(claims.get("sub")),
        tenant_id=tenant_id,
        roles=roles,
        org_unit=claims.get("org_unit"),
        raw_claims=claims,
    )


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Validate OIDC bearer tokens and attach tenant context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings: Settings = request.app.state.settings
        public_paths = {
            "/api/v1/health",
            "/api/v1/openapi.json",
            "/api/v1/docs",
            "/api/v1/capabilities",
        }
        if request.url.path in public_paths:
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return problem_response(
                status=401,
                title="Unauthorized",
                detail="Bearer token required",
                type_uri="https://cleartrace.local/problems/unauthorized",
            )
        token = auth.removeprefix("Bearer ").strip()
        try:
            ctx = await decode_bearer_token(settings, token)
        except Exception as exc:
            return problem_response(
                status=401,
                title="Unauthorized",
                detail=str(exc),
                type_uri="https://cleartrace.local/problems/unauthorized",
            )
        if settings.dev_skip_auth:
            dev_roles = _dev_roles_from_request(request)
            raw_claims = dict(ctx.raw_claims)
            principal = request.headers.get("X-ClearTrace-Dev-Principal", "").strip()
            if principal:
                raw_claims["principal_id"] = principal
            if dev_roles is not None or principal:
                ctx = AuthContext(
                    subject=ctx.subject,
                    tenant_id=ctx.tenant_id,
                    roles=dev_roles if dev_roles is not None else ctx.roles,
                    org_unit=ctx.org_unit,
                    raw_claims=raw_claims,
                )
        request.state.auth = ctx
        return await call_next(request)


class CedarAuthMiddleware(BaseHTTPMiddleware):
    """Deny requests that fail Cedar authorization for the route action."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        public_paths = {
            "/api/v1/health",
            "/api/v1/openapi.json",
            "/api/v1/docs",
            "/api/v1/capabilities",
        }
        if request.url.path in public_paths:
            return await call_next(request)
        auth: AuthContext | None = getattr(request.state, "auth", None)
        if auth is None:
            return problem_response(
                status=401,
                title="Unauthorized",
                detail="Missing auth context",
                type_uri="https://cleartrace.local/problems/unauthorized",
            )
        authorizer: CedarAuthorizer = request.app.state.cedar_authorizer
        action = action_for_request(request)
        principal = {
            "type": "ClearTrace::User",
            "id": auth.subject,
            "attrs": {
                "tenant_id": str(auth.tenant_id),
                "roles": sorted(auth.roles),
                "org_unit": auth.org_unit or "",
            },
        }
        resource = {
            "type": "ClearTrace::Api",
            "id": request.url.path,
            "attrs": {"tenant_id": str(auth.tenant_id)},
        }
        if not authorizer.is_authorized(
            principal=principal,
            action=action,
            resource=resource,
            context={
                "tenant_id": str(auth.tenant_id),
                "roles": sorted(auth.roles),
            },
        ):
            _audit_authz_denial(request, auth, action)
            return problem_response(
                status=403,
                title="Forbidden",
                detail="Cedar policy denied this action",
                type_uri="https://cleartrace.local/problems/forbidden",
            )
        return await call_next(request)


def _audit_authz_denial(request: Request, auth: AuthContext, action: str) -> None:
    settings: Settings = request.app.state.settings
    ledger = get_audit_ledger(request)
    try:
        with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
            ledger.append_event_tx(
                conn,
                tenant_id=auth.tenant_id,
                actor_id=None,
                action="authz.denied",
                resource_type="api",
                resource_id=None,
                payload={"attempted_action": action, "path": request.url.path},
            )
    except Exception:
        return
