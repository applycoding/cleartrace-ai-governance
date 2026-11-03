from __future__ import annotations

import pytest
from cleartrace_core_api.data_policy.crypto import encrypt_record, tombstone_hash


def test_encrypt_and_tombstone() -> None:
    blob = encrypt_record(b"secret-bytes")
    assert blob.ciphertext
    assert len(blob.content_hash) == 64
    ts = tombstone_hash(blob.content_hash, "payload-1")
    assert len(ts) == 64


def test_no_built_in_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from cleartrace_core_api.data_policy import crypto

    monkeypatch.delenv("CLEARTRACE_DATA_MASTER_KEY", raising=False)
    assert crypto._master_key() == crypto._EPHEMERAL_MASTER_KEY
    assert b"cleartrace-test-master-key" not in crypto._master_key()
    monkeypatch.setenv("CLEARTRACE_DATA_MASTER_KEY", "too-short")
    with pytest.raises(crypto.MasterKeyError):
        encrypt_record(b"x")
    monkeypatch.setenv("CLEARTRACE_DATA_MASTER_KEY", "k" * 40)
    assert len(crypto._master_key()) == 32
    assert encrypt_record(b"x").wrapped_key
