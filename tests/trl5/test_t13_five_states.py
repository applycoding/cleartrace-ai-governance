from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control

pytestmark = pytest.mark.usefixtures("opa_server")

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"
REPLAY = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"
PACKS = ROOT / "policies" / "packs"


@pytest.mark.parametrize("case", json.loads(GOLDEN.read_text(encoding="utf-8")))
def test_t13_golden_outcome(case: dict) -> None:
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


def test_t13_golden_file_has_250_cases_and_state_balance() -> None:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(cases) == 250
    states = {c["expect"]["outcome_state"] for c in cases}
    assert states == {
        "not_applicable",
        "met",
        "partially_met",
        "not_met",
        "unable_to_determine",
    }
    for state in states:
        assert sum(1 for c in cases if c["expect"]["outcome_state"] == state) == 50
    assert sum(1 for c in cases if c["expect"]["outcome_state"] == "partially_met") >= 30
    slugs = {c["pack_slug"] for c in cases}
    assert "golden" not in slugs
    assert len(slugs) >= 5


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
