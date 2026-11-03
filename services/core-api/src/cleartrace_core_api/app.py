from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from cleartrace_notifier.router import register_notifier_routes
from cleartrace_notifier.service import NotifierService
from cleartrace_register.api.router import mount_register_routes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from cleartrace_core_api.auth.cedar_engine import CedarAuthorizer
from cleartrace_core_api.auth.middleware import AuthContextMiddleware, CedarAuthMiddleware
from cleartrace_core_api.config import Settings
from cleartrace_core_api.errors import register_exception_handlers
from cleartrace_core_api.middleware.idempotency import IdempotencyMiddleware
from cleartrace_core_api.middleware.json_input_guard import JsonInputGuardMiddleware
from cleartrace_core_api.middleware.language import LanguageMiddleware
from cleartrace_core_api.middleware.optimistic_lock import OptimisticLockMiddleware
from cleartrace_core_api.middleware.security_headers import SecurityHeadersMiddleware
from cleartrace_core_api.middleware.tenant_rate_limit import TenantRateLimitMiddleware
from cleartrace_core_api.openapi_contract import (
    IDEMPOTENCY_KEY_PATTERN,
    apply_contract_annotations,
)
from cleartrace_core_api.routers import (
    admin,
    aia,
    assessments,
    audit,
    connectors,
    data_policy,
    evidence,
    findings,
    frameworks,
    health,
    interop,
    policy_watch,
    reports,
    risk,
    systems,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.cedar_authorizer = CedarAuthorizer(cfg.cedar_policy_path)
        yield

    app = FastAPI(
        title="ClearTrace Governance API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url=None,
        lifespan=lifespan,
    )
    static_root = Path(__file__).resolve().parents[2] / "static"
    if (static_root / "swagger-ui").is_dir():
        app.mount(
            "/api/v1/swagger-ui",
            StaticFiles(directory=str(static_root / "swagger-ui")),
            name="swagger-ui",
        )

    @app.get("/api/v1/docs", include_in_schema=False)
    async def swagger_ui() -> object:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/api/v1/openapi.json",
            title=f"{app.title} – API docs",
            swagger_js_url="/api/v1/swagger-ui/swagger-ui-bundle.js",
            swagger_css_url="/api/v1/swagger-ui/swagger-ui.css",
        )
    app.state.settings = cfg
    app.state.cedar_authorizer = CedarAuthorizer(cfg.cedar_policy_path)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(JsonInputGuardMiddleware)
    app.add_middleware(LanguageMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(OptimisticLockMiddleware)
    app.add_middleware(CedarAuthMiddleware)
    app.add_middleware(TenantRateLimitMiddleware)
    app.add_middleware(AuthContextMiddleware)
    # Outermost, so 401/403/429 problem responses from the auth layers carry it too.
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)

    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(systems.router, prefix=prefix)
    app.include_router(frameworks.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(evidence.router, prefix=prefix)
    app.include_router(findings.router, prefix=prefix)
    app.include_router(assessments.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)
    app.include_router(data_policy.router, prefix=prefix)
    app.include_router(interop.router, prefix=prefix)
    app.include_router(aia.router, prefix=prefix)
    app.include_router(connectors.router, prefix=prefix)
    app.include_router(policy_watch.router, prefix=prefix)
    app.include_router(risk.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    mount_register_routes(app, prefix=prefix)
    register_notifier_routes(app, NotifierService())
    _document_common_errors(app)

    return app


# Matches IdempotencyMiddleware: 1-128 visible ASCII characters, no spaces.
_IDEMPOTENCY_KEY_SCHEMA: dict[str, object] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 128,
    "pattern": IDEMPOTENCY_KEY_PATTERN,
}
_PROBLEM_CONTENT = {"application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}}
# Responses the middleware stack can return on any protected operation.
_COMMON_ERRORS: dict[str, str] = {
    "400": "Bad request (for example an invalid dev or language header)",
    "401": "Missing or invalid bearer token",
    "403": "Cedar policy denied this action",
    "404": "Resource not found or not visible to this tenant",
    "409": "Conflict (idempotency key reuse or state conflict)",
    "412": "If-Match precondition failed",
    "428": "If-Match required",
    "429": "Per-tenant rate limit exceeded",
}
_PUBLIC_OPENAPI_PATHS = {"/api/v1/health", "/api/v1/capabilities"}


def _document_common_errors(app: FastAPI) -> None:
    """Add the shared problem+json error responses to every protected operation."""

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        from cleartrace_contracts.models import ProblemDetail
        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas.setdefault(
            "ProblemDetail",
            ProblemDetail.model_json_schema(ref_template="#/components/schemas/{model}"),
        )
        components.setdefault("securitySchemes", {})["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
        for path, operations in schema.get("paths", {}).items():
            public = path in _PUBLIC_OPENAPI_PATHS
            for op in operations.values():
                if not isinstance(op, dict) or "responses" not in op:
                    continue
                if public:
                    op["security"] = []
                    continue
                op.setdefault("security", [{"bearerAuth": []}])
                if path.startswith("/api/v1/systems") and op is operations.get("post"):
                    # IdempotencyMiddleware rejects POSTs under /systems without it.
                    params = op.setdefault("parameters", [])
                    if not any(p.get("name") == "Idempotency-Key" for p in params):
                        params.append(
                            {
                                "name": "Idempotency-Key",
                                "in": "header",
                                "required": True,
                                "schema": dict(_IDEMPOTENCY_KEY_SCHEMA),
                            }
                        )
                    for p in params:
                        if p.get("name") == "Idempotency-Key":
                            p["required"] = True
                            p["schema"] = dict(_IDEMPOTENCY_KEY_SCHEMA)
                # The validation handler answers 422 as problem+json, not FastAPI's default body.
                op["responses"]["422"] = {
                    "description": "Request validation failed",
                    "content": _PROBLEM_CONTENT,
                }
                for code, description in _COMMON_ERRORS.items():
                    op["responses"].setdefault(
                        code, {"description": description, "content": _PROBLEM_CONTENT}
                    )
        apply_contract_annotations(schema)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
