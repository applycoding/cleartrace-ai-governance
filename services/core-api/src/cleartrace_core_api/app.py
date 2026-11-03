from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from cleartrace_notifier.router import register_notifier_routes
from cleartrace_notifier.service import NotifierService
from cleartrace_register.api.router import mount_register_routes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cleartrace_core_api.auth.cedar_engine import CedarAuthorizer
from cleartrace_core_api.auth.middleware import AuthContextMiddleware, CedarAuthMiddleware
from cleartrace_core_api.config import Settings
from cleartrace_core_api.errors import register_exception_handlers
from cleartrace_core_api.middleware.idempotency import IdempotencyMiddleware
from cleartrace_core_api.middleware.language import LanguageMiddleware
from cleartrace_core_api.middleware.optimistic_lock import OptimisticLockMiddleware
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
        docs_url="/api/v1/docs",
        lifespan=lifespan,
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
    app.add_middleware(LanguageMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(OptimisticLockMiddleware)
    app.add_middleware(CedarAuthMiddleware)
    app.add_middleware(AuthContextMiddleware)

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

    return app
