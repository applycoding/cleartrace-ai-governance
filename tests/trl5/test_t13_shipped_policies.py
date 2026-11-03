from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control

pytestmark = pytest.mark.usefixtures("opa_server")

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "policies" / "packs"
MIXED = ROOT / "tests" / "trl5" / "fixtures" / "t13_shipped_mixed_cases.json"
REPLAY = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"


@pytest.mark.parametrize("case", json.loads(MIXED.read_text(encoding="utf-8")))
def test_t13_shipped_policy_mixed_cases(case: dict) -> None:
    pack = load_pack(PACKS / case["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == case["control_key"])
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=case["system"],
        evidence=case.get("evidence", []),
        pack_slug=case["pack_slug"],
        cel_context=case["system"],
    )
    expect = case["expect"]
    assert output.outcome_state == expect["outcome_state"]
    assert output.reason_code == expect["reason_code"]


def test_t13_shipped_mixed_case_count() -> None:
    cases = json.loads(MIXED.read_text(encoding="utf-8"))
    assert len(cases) >= 30
    assert any(c["expect"]["outcome_state"] == "partially_met" for c in cases)


@pytest.mark.parametrize("entry", json.loads(REPLAY.read_text(encoding="utf-8")))
def test_t13_rule_only_replay_is_byte_identical(entry: dict) -> None:
    pack = load_pack(PACKS / entry["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == entry["control_key"])
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=entry["system"],
        evidence=entry.get("evidence", []),
        pack_slug=entry["pack_slug"],
        cel_context=entry["system"],
    )
    replay_bytes = json.dumps(asdict(output), sort_keys=True).encode("utf-8")
    stored_bytes = json.dumps(entry["snapshot"], sort_keys=True).encode("utf-8")
    assert replay_bytes == stored_bytes
