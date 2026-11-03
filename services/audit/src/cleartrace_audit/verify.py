from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from psycopg import Connection

from cleartrace_audit.canonical import canonical_json_bytes, sha256_hex
from cleartrace_audit.checkpoint import merkle_root
from cleartrace_audit.worm import WormObjectStore


@dataclass
class TamperFinding:
    kind: str
    row_index: int | None
    detail: str


@dataclass
class VerificationReport:
    tenant_id: UUID
    ok: bool
    tree_size: int
    checkpoint_count: int
    exposure_window_seconds: int = 60
    findings: list[TamperFinding] = field(default_factory=list)


def verify_tenant_chain(
    conn: Connection[Any],
    *,
    tenant_id: UUID,
    worm_root: Any,
) -> VerificationReport:
    worm = WormObjectStore(worm_root)
    findings: list[TamperFinding] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, actor_id, prev_hash, event_hash, action, resource_type, resource_id, payload, occurred_at
            FROM audit_event
            WHERE tenant_id = %s
            ORDER BY occurred_at ASC, id ASC
            """,
            (tenant_id,),
        )
        rows = cur.fetchall()
    expected_prev = "0" * 64
    event_hashes: list[str] = []
    for idx, row in enumerate(rows):
        (
            _eid,
            actor_id,
            prev_hash,
            event_hash,
            action,
            resource_type,
            resource_id,
            payload,
            _occurred,
        ) = row
        if str(prev_hash) != expected_prev:
            findings.append(
                TamperFinding(
                    kind="broken_chain",
                    row_index=idx,
                    detail=f"prev_hash mismatch at row {idx}",
                )
            )
        body = {
            "tenant_id": str(tenant_id),
            "actor_id": str(actor_id) if actor_id else None,
            "action": str(action),
            "resource_type": str(resource_type),
            "resource_id": str(resource_id) if resource_id else None,
            "payload": payload if isinstance(payload, dict) else {},
        }
        recomputed = sha256_hex(canonical_json_bytes({"prev_hash": str(prev_hash), "body": body}))
        if str(event_hash) != recomputed:
            findings.append(
                TamperFinding(
                    kind="edited_event",
                    row_index=idx,
                    detail=f"event_hash mismatch at row {idx}",
                )
            )
        expected_prev = str(event_hash)
        event_hashes.append(str(event_hash))

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tree_size, root_hash, worm_uri, leaf_manifest_uri
            FROM merkle_checkpoint
            WHERE tenant_id = %s
            ORDER BY created_at ASC
            """,
            (tenant_id,),
        )
        checkpoints = cur.fetchall()

    tree_size = len(rows)
    for cp_idx, (cp_size, cp_root, worm_uri, leaf_uri) in enumerate(checkpoints):
        if int(cp_size) > tree_size:
            findings.append(
                TamperFinding(
                    kind="truncation",
                    row_index=cp_idx,
                    detail=f"checkpoint tree_size {cp_size} exceeds live rows {tree_size}",
                )
            )
        if merkle_root(event_hashes[: int(cp_size)]) != str(cp_root):
            findings.append(
                TamperFinding(
                    kind="reordered_or_deleted",
                    row_index=cp_idx,
                    detail=f"checkpoint root mismatch at checkpoint {cp_idx}",
                )
            )
        try:
            worm.read(str(worm_uri))
            worm.read(str(leaf_uri))
        except OSError as exc:
            findings.append(
                TamperFinding(
                    kind="worm_missing",
                    row_index=cp_idx,
                    detail=str(exc),
                )
            )

    return VerificationReport(
        tenant_id=tenant_id,
        ok=len(findings) == 0,
        tree_size=tree_size,
        checkpoint_count=len(checkpoints),
        findings=findings,
    )
