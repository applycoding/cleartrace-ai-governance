from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def admin_ping(request: Request) -> dict[str, str]:
    auth = request.state.auth
    return {"tenant_id": str(auth.tenant_id), "subject": auth.subject}
