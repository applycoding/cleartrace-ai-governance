from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from cleartrace_core_api.deps import get_audit_ledger
from cleartrace_core_api.errors import problem_response

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventItem(BaseModel):
    id: UUID
    occurred_at: datetime
    action: str
    resource_type: str
    resource_id: UUID | None
    event_hash: str


class AuditEventPage(BaseModel):
    items: list[AuditEventItem]
    tree_size: int


@router.get("/events", response_model=AuditEventPage)
async def list_audit_events(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AuditEventPage | object:
    auth = request.state.auth
    if "auditor" not in auth.roles and "tenant_admin" not in auth.roles:
        return problem_response(status=403, title="Forbidden", detail="Auditor role required")
    settings = request.app.state.settings
    ledger = get_audit_ledger(request)
    with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
        ledger.append_event_tx(
            conn,
            tenant_id=auth.tenant_id,
            actor_id=UUID(str(auth.raw_claims.get("principal_id") or auth.subject)),
            action="audit.read",
            resource_type="audit_ledger",
            resource_id=None,
            payload={"path": "/audit/events"},
            pii_plaintext=None,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, occurred_at, action, resource_type, resource_id, event_hash
                FROM audit_event
                WHERE tenant_id = %s
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
                (auth.tenant_id, limit),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*)::int FROM audit_event WHERE tenant_id = %s",
                (auth.tenant_id,),
            )
            count_row = cur.fetchone()
    tree_size = int(count_row[0]) if count_row else 0
    items = [
        AuditEventItem(
            id=row[0],
            occurred_at=row[1],
            action=str(row[2]),
            resource_type=str(row[3]),
            resource_id=row[4],
            event_hash=str(row[5]),
        )
        for row in rows
    ]
    return AuditEventPage(items=items, tree_size=tree_size)
