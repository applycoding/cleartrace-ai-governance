from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Json
from uuid6 import uuid7

from cleartrace_audit.canonical import canonical_json_bytes, sha256_hex
from cleartrace_audit.checkpoint import build_checkpoint
from cleartrace_audit.signer import load_checkpoint_signer_key, sign_tree_head
from cleartrace_audit.worm import WormObjectStore


class AuditLedgerService:
    CHECKPOINT_EVENT_INTERVAL = 1000

    def __init__(
        self,
        *,
        worm_root: Any,
        signer_key_path: Any,
    ) -> None:
        self._worm = WormObjectStore(worm_root)
        self._signer_key_path = signer_key_path
        self._events_since_checkpoint: dict[str, int] = {}

    async def append_event(self, tenant_id: UUID, event: dict[str, object]) -> UUID:
        raise NotImplementedError("Use append_event_tx inside a DB transaction")

    def append_event_tx(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        payload: dict[str, object],
        pii_plaintext: str | None = None,
    ) -> UUID:
        event_id = uuid7()
        prev_hash = self._last_hash(conn, tenant_id)
        body = {
            "tenant_id": str(tenant_id),
            "actor_id": str(actor_id) if actor_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "payload": payload,
        }
        event_hash = sha256_hex(canonical_json_bytes({"prev_hash": prev_hash, "body": body}))
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_event (
                  id, tenant_id, actor_id, action, resource_type, resource_id,
                  prev_hash, event_hash, payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    event_id,
                    tenant_id,
                    actor_id,
                    action,
                    resource_type,
                    resource_id,
                    prev_hash,
                    event_hash,
                    Json(payload),
                ),
            )
        if pii_plaintext:
            commitment = sha256_hex(pii_plaintext.encode("utf-8"))
            ciphertext = _xor_obfuscate(pii_plaintext.encode("utf-8"), commitment)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_pii (id, tenant_id, audit_event_id, commitment_hash, payload_ciphertext)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (uuid7(), tenant_id, event_id, commitment, ciphertext),
                )
        self._maybe_checkpoint(conn, tenant_id)
        return event_id

    def _last_hash(self, conn: Connection[Any], tenant_id: UUID) -> str:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_hash FROM audit_event
                WHERE tenant_id = %s
                ORDER BY occurred_at ASC, id ASC
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
        if not rows:
            return "0" * 64
        return str(rows[-1][0])

    def _maybe_checkpoint(self, conn: Connection[Any], tenant_id: UUID) -> None:
        key = str(tenant_id)
        self._events_since_checkpoint[key] = self._events_since_checkpoint.get(key, 0) + 1
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*)::bigint FROM audit_event WHERE tenant_id = %s",
                (tenant_id,),
            )
            row = cur.fetchone()
        tree_size = int(row[0]) if row else 0
        if (
            self._events_since_checkpoint[key] < self.CHECKPOINT_EVENT_INTERVAL
            and tree_size % self.CHECKPOINT_EVENT_INTERVAL != 0
        ):
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_hash FROM audit_event
                WHERE tenant_id = %s
                ORDER BY occurred_at ASC, id ASC
                """,
                (tenant_id,),
            )
            hashes = [str(r[0]) for r in cur.fetchall()]
        signer = load_checkpoint_signer_key(self._signer_key_path)
        result = build_checkpoint(
            event_hashes=hashes,
            tree_size=tree_size,
            sign_fn=lambda head: sign_tree_head(signer, head),
            worm_store=self._worm,
            tenant_id=str(tenant_id),
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO merkle_checkpoint (
                  id, tenant_id, tree_size, root_hash, signed_tree_head, worm_uri, leaf_manifest_uri
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid7(),
                    tenant_id,
                    result.tree_size,
                    result.root_hash,
                    result.signed_tree_head,
                    result.worm_uri,
                    result.leaf_manifest_uri,
                ),
            )
        self._events_since_checkpoint[key] = 0


def _xor_obfuscate(data: bytes, key_hex: str) -> bytes:
    key = hashlib.sha256(key_hex.encode("utf-8")).digest()
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
