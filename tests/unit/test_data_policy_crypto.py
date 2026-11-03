from __future__ import annotations

from cleartrace_core_api.data_policy.crypto import encrypt_record, tombstone_hash


def test_encrypt_and_tombstone() -> None:
    blob = encrypt_record(b"secret-bytes")
    assert blob.ciphertext
    assert len(blob.content_hash) == 64
    ts = tombstone_hash(blob.content_hash, "payload-1")
    assert len(ts) == 64
