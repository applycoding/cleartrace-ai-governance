"""FastAPI routes for notifications and webhooks (mount from core-api when integrated)."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from uuid6 import uuid7

from cleartrace_notifier.models import WebhookSubscription
from cleartrace_notifier.service import NotifierService
from cleartrace_notifier.webhook import WebhookURLError, validate_webhook_url

router = APIRouter(tags=["notifications"])


class WebhookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(
        max_length=2048,
        pattern=(
            r"^https://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
            r"[A-Za-z]{2,63}(:[0-9]{1,5})?(?:/[^\s?#]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?$"
        ),
    )
    secret: str = Field(min_length=16, max_length=256)
    channel: str = Field(default="generic", pattern=r"^[a-z][a-z0-9_-]{0,31}$")


class AlertCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_type: str
    system_id: UUID | None = None
    control_id: str | None = None
    reason: str
    title_en: str
    title_fr: str
    body_en: str = ""
    body_fr: str = ""
    event_id: str | None = None


def register_notifier_routes(
    app: Any,
    service: NotifierService | None = None,
    *,
    prefix: str = "/api/v1",
) -> None:
    app.state.notifier_service = service or NotifierService()
    app.include_router(router, prefix=prefix)


def _service(request: Request) -> NotifierService:
    svc = getattr(request.app.state, "notifier_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="notifier not configured")
    return cast(NotifierService, svc)


def _tenant_id(request: Request) -> UUID:
    auth = request.state.auth
    return UUID(str(auth.tenant_id))


@router.get("/notifications")
async def list_notifications(request: Request) -> dict[str, list[dict[str, str]]]:
    svc = _service(request)
    tenant_id = _tenant_id(request)
    items = [
        {
            "id": str(n.id),
            "status": n.status.value,
            "reason": n.alert.reason,
        }
        for n in svc.store.open_notifications()
        if n.tenant_id == tenant_id
    ]
    return {"items": items}


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate, request: Request) -> dict[str, str]:
    svc = _service(request)
    tenant_id = _tenant_id(request)
    try:
        validate_webhook_url(body.url)
    except WebhookURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sub = WebhookSubscription(
        id=uuid7(),
        tenant_id=tenant_id,
        url=body.url,
        secret=body.secret,
        channel=body.channel,
    )
    svc.store.save_subscription(sub)
    return {"id": str(sub.id), "url": sub.url}


@router.post("/notifications:dispatch")
async def dispatch_alert(body: AlertCreate, request: Request) -> dict[str, object]:
    svc = _service(request)
    tenant_id = _tenant_id(request)
    await svc.dispatch_alert(tenant_id, body.model_dump())
    return {"status": "accepted"}
