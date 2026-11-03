from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class EncryptedBlob:
    ciphertext: bytes
    content_hash: str
    wrapped_key: bytes


MIN_MASTER_KEY_BYTES = 32
# Without a configured key each process gets a random one, so wrapped keys only live as
# long as the process. There is no built-in default key (ASVS V2.10.4, V6.4.1).
_EPHEMERAL_MASTER_KEY = AESGCM.generate_key(bit_length=256)


class MasterKeyError(ValueError):
    """CLEARTRACE_DATA_MASTER_KEY is set but too short to use."""


def _master_key() -> bytes:
    configured = os.environ.get("CLEARTRACE_DATA_MASTER_KEY")
    if configured is None or configured == "":
        return _EPHEMERAL_MASTER_KEY
    raw = configured.encode("utf-8")
    if len(raw) < MIN_MASTER_KEY_BYTES:
        msg = f"CLEARTRACE_DATA_MASTER_KEY must be at least {MIN_MASTER_KEY_BYTES} bytes"
        raise MasterKeyError(msg)
    return hashlib.sha256(raw).digest()


def encrypt_record(plaintext: bytes, *, aad: bytes = b"cleartrace-record") -> EncryptedBlob:
    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    aes = AESGCM(data_key)
    ciphertext = nonce + aes.encrypt(nonce, plaintext, aad)
    content_hash = hashlib.sha256(plaintext).hexdigest()
    master = _master_key()
    wrap_nonce = os.urandom(12)
    wrap_aes = AESGCM(master)
    wrapped_key = wrap_nonce + wrap_aes.encrypt(wrap_nonce, data_key, aad)
    return EncryptedBlob(ciphertext=ciphertext, content_hash=content_hash, wrapped_key=wrapped_key)


def destroy_wrapped_key(wrapped_key: bytes) -> bytes:
    """Simulate KMS key destruction by overwriting wrapped key material."""
    return b"\x00" * len(wrapped_key)


def tombstone_hash(content_hash: str, payload_id: str) -> str:
    return hashlib.sha256(f"{content_hash}:{payload_id}:tombstone".encode()).hexdigest()
