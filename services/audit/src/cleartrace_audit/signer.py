from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat


def load_checkpoint_signer_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        raw = path.read_bytes()
        return Ed25519PrivateKey.from_private_bytes(raw)
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
    os.chmod(path, 0o600)
    return key


def sign_tree_head(private_key: Ed25519PrivateKey, tree_head: str) -> str:
    sig = private_key.sign(tree_head.encode("utf-8"))
    return base64.b64encode(sig).decode("ascii")
