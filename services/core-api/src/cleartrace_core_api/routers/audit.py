from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from cleartrace_audit.verify import verify_tenant_chain
from cleartrace_db.session import tenant_transaction
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from cleartrace_core_api.deps import get_audit_ledger

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
    settings = request.app.state.settings
    ledger = get_audit_ledger(request)
    with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
        ledger.append_event_tx(
            conn,
            tenant_id=auth.tenant_id,
            actor_id=auth.actor_id,
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


class AuditCheckpointItem(BaseModel):
    tree_size: int
    root_hash: str
    worm_uri: str | None


@router.get("/checkpoints", response_model=list[AuditCheckpointItem])
async def list_checkpoints(request: Request) -> list[AuditCheckpointItem]:
    auth = request.state.auth
    settings = request.app.state.settings
    with tenant_transaction(settings.database_url, auth.tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT tree_size, root_hash, worm_uri
            FROM merkle_checkpoint
            WHERE tenant_id = %s
            ORDER BY tree_size DESC
            LIMIT 20
            """,
            (auth.tenant_id,),
        )
        rows = cur.fetchall()
    return [
        AuditCheckpointItem(tree_size=int(row[0]), root_hash=str(row[1]), worm_uri=row[2])
        for row in rows
    ]


class AuditVerifyResponse(BaseModel):
    ok: bool
    tree_size: int
    failure_count: int
    checkpoint_count: int


@router.post(":verify", response_model=AuditVerifyResponse)
async def verify_audit(request: Request) -> AuditVerifyResponse:
    auth = request.state.auth
    settings = request.app.state.settings
    worm_root = Path(settings.audit_worm_root)
    with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
        report = verify_tenant_chain(
            conn,
            tenant_id=auth.tenant_id,
            worm_root=worm_root,
        )
    return AuditVerifyResponse(
        ok=report.ok,
        tree_size=report.tree_size,
        failure_count=len(report.findings),
        checkpoint_count=report.checkpoint_count,
    )
