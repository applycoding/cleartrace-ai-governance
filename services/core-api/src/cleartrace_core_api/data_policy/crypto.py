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


def encrypt_record(plaintext: bytes, *, aad: bytes = b"cleartrace-record") -> EncryptedBlob:
    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    aes = AESGCM(data_key)
    ciphertext = nonce + aes.encrypt(nonce, plaintext, aad)
    content_hash = hashlib.sha256(plaintext).hexdigest()
    master_raw = os.environ.get(
        "CLEARTRACE_DATA_MASTER_KEY",
        "cleartrace-test-master-key-32b!!",
    )
    master = master_raw.encode()
    wrap_nonce = os.urandom(12)
    wrap_aes = AESGCM(master[:32].ljust(32, b"0")[:32])
    wrapped_key = wrap_nonce + wrap_aes.encrypt(wrap_nonce, data_key, aad)
    return EncryptedBlob(ciphertext=ciphertext, content_hash=content_hash, wrapped_key=wrapped_key)


def destroy_wrapped_key(wrapped_key: bytes) -> bytes:
    """Simulate KMS key destruction by overwriting wrapped key material."""
    return b"\x00" * len(wrapped_key)


def tombstone_hash(content_hash: str, payload_id: str) -> str:
    return hashlib.sha256(f"{content_hash}:{payload_id}:tombstone".encode()).hexdigest()
