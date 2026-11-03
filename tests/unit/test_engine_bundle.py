from __future__ import annotations

from pathlib import Path

from cleartrace_engine.evaluate import bundle_digest


def test_bundle_digest_is_stable() -> None:
    root = Path(__file__).resolve().parents[2] / "policies" / "rego"
    first = bundle_digest(root)
    second = bundle_digest(root)
    assert first == second
    assert len(first) == 64
