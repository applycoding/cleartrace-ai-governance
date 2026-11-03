from __future__ import annotations

from cleartrace_audit.canonical import canonical_json_bytes, sha256_hex
from cleartrace_evidence.constants import ARTEFACT_CLASSES
from cleartrace_evidence.scanner import scan_upload


def test_all_eight_artefact_classes_defined() -> None:
    assert len(ARTEFACT_CLASSES) == 8


def test_scanner_rejects_oversized_payload() -> None:
    big = b"x" * (50 * 1024 * 1024 + 1)
    result = scan_upload(big, "application/pdf")
    assert result.ok is False


def test_canonical_json_stable() -> None:
    a = sha256_hex(canonical_json_bytes({"b": 1, "a": 2}))
    b = sha256_hex(canonical_json_bytes({"a": 2, "b": 1}))
    assert a == b
