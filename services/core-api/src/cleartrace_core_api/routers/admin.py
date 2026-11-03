from __future__ import annotations

from fastapi import APIRouter, Request

from cleartrace_core_api.privileged_read import record_privileged_read

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def admin_ping(request: Request) -> dict[str, str]:
    auth = request.state.auth
    record_privileged_read(request, action="admin.read", resource_type="admin", payload={})
    return {"tenant_id": str(auth.tenant_id), "subject": auth.subject}
