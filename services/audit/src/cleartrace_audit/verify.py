from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
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
    checkpoint_index: int | None = None


@dataclass
class VerificationReport:
    tenant_id: UUID
    ok: bool
    tree_size: int
    checkpoint_count: int
    # Exposure window: live rows appended after the newest checkpoint. They are
    # protected only by the hash chain, which a writer with database access could
    # recompute, until the next signed checkpoint anchors them in WORM storage.
    exposure_window_events: int = 0
    exposure_window_seconds: float = 0.0
    exposure_window_start: str | None = None
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
            SELECT tree_size, root_hash, worm_uri, leaf_manifest_uri, created_at
            FROM merkle_checkpoint
            WHERE tenant_id = %s
            ORDER BY created_at ASC
            """,
            (tenant_id,),
        )
        checkpoints = cur.fetchall()

    tree_size = len(rows)
    for cp_idx, (cp_size, cp_root, worm_uri, leaf_uri, _created) in enumerate(checkpoints):
        size = int(cp_size)
        anchored_leaves: list[str] | None = None
        try:
            worm.read(str(worm_uri))
            anchored_leaves = _manifest_leaves(worm.read(str(leaf_uri)))
        except (OSError, ValueError) as exc:
            findings.append(
                TamperFinding(
                    kind="worm_missing",
                    row_index=None,
                    detail=str(exc),
                    checkpoint_index=cp_idx,
                )
            )
        if size > tree_size:
            findings.append(
                TamperFinding(
                    kind="truncation",
                    row_index=tree_size,
                    detail=(
                        f"checkpoint {cp_idx} anchors {size} rows but only {tree_size} "
                        f"live rows remain; rows {tree_size}..{size - 1} are missing"
                    ),
                    checkpoint_index=cp_idx,
                )
            )
        if merkle_root(event_hashes[:size]) != str(cp_root):
            located = _first_divergent_row(anchored_leaves, event_hashes, size)
            findings.append(
                TamperFinding(
                    kind="reordered_or_deleted",
                    row_index=located,
                    detail=(
                        f"checkpoint {cp_idx} root mismatch; first divergent row {located}"
                        if located is not None
                        else f"checkpoint {cp_idx} root mismatch; leaf manifest unavailable"
                    ),
                    checkpoint_index=cp_idx,
                )
            )

    anchored = max((int(cp[0]) for cp in checkpoints), default=0)
    exposed = rows[anchored:]
    window_events = len(exposed)
    window_seconds = 0.0
    window_start: str | None = None
    if exposed:
        last_cp_at = checkpoints[-1][4] if checkpoints else None
        start = last_cp_at if isinstance(last_cp_at, datetime) else exposed[0][8]
        end = exposed[-1][8]
        if isinstance(start, datetime) and isinstance(end, datetime):
            window_start = start.isoformat()
            window_seconds = max(0.0, (end - start).total_seconds())

    return VerificationReport(
        tenant_id=tenant_id,
        ok=len(findings) == 0,
        tree_size=tree_size,
        checkpoint_count=len(checkpoints),
        exposure_window_events=window_events,
        exposure_window_seconds=window_seconds,
        exposure_window_start=window_start,
        findings=findings,
    )


def _manifest_leaves(raw: bytes) -> list[str]:
    doc = json.loads(raw)
    leaves = doc.get("leaves") if isinstance(doc, dict) else None
    if not isinstance(leaves, list):
        raise ValueError("checkpoint leaf manifest has no leaves list")
    return [str(leaf) for leaf in leaves]


def _first_divergent_row(
    anchored: list[str] | None, live: list[str], size: int
) -> int | None:
    """Index of the first live row whose hash differs from the WORM-anchored leaf."""
    if anchored is None:
        return None
    for idx in range(size):
        if idx >= len(live) or idx >= len(anchored) or live[idx] != anchored[idx]:
            return idx
    return None
