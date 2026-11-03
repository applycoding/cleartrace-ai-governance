from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from uuid6 import uuid7

from cleartrace_audit.canonical import canonical_json_bytes, sha256_hex


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return sha256_hex(b"")
    layer = [bytes.fromhex(h) for h in hashes]
    while len(layer) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
    return layer[0].hex()


@dataclass(frozen=True)
class CheckpointResult:
    tree_size: int
    root_hash: str
    signed_tree_head: str
    worm_uri: str
    leaf_manifest_uri: str


def build_checkpoint(
    *,
    event_hashes: list[str],
    tree_size: int,
    sign_fn: Any,
    worm_store: Any,
    tenant_id: str,
) -> CheckpointResult:
    root = merkle_root(event_hashes)
    tree_head = f"{tenant_id}:{tree_size}:{root}"
    signed = sign_fn(tree_head)
    manifest = canonical_json_bytes(
        {"tenant_id": tenant_id, "tree_size": tree_size, "leaves": event_hashes}
    )
    stamp = uuid7().hex
    worm_uri = worm_store.put_worm(
        f"{tenant_id}/sth-{tree_size}-{stamp}.json",
        canonical_json_bytes({"tree_head": tree_head, "signed_tree_head": signed}),
        {"tree_size": tree_size, "root_hash": root},
    )
    leaf_uri = worm_store.put_worm(
        f"{tenant_id}/leaves-{tree_size}-{stamp}.json",
        manifest,
        {"tree_size": tree_size},
    )
    return CheckpointResult(
        tree_size=tree_size,
        root_hash=root,
        signed_tree_head=signed,
        worm_uri=worm_uri,
        leaf_manifest_uri=leaf_uri,
    )
