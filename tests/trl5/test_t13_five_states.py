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


def _run(case: dict, system: dict, evidence: list) -> tuple[str, str]:
    pack = load_pack(PACKS / case["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == case["control_key"])
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=system,
        evidence=evidence,
        pack_slug=case["pack_slug"],
        cel_context=system,
    )
    return output.outcome_state, output.reason_code


def _canonical_input(case: dict) -> str:
    """The case input with every field the engine ignores for this control removed."""
    system = dict(case["system"])
    evidence = list(case["evidence"])
    if case["variation"] == "unrelated_evidence_added":
        evidence = evidence[:-1]
    target = (case["expect"]["outcome_state"], case["expect"]["reason_code"])
    if "impact_level" in system:
        # Replace the level by the set of levels that give this same result.
        same = [lvl for lvl in (1, 2, 3, 4) if _run(case, {**system, "impact_level": lvl}, evidence) == target]
        system["impact_level"] = "any" if len(same) == 4 else same
    if evidence and _run(case, case["system"], []) == target and target[0] == "not_applicable":
        evidence = []
    return json.dumps([case["control_key"], system, evidence], sort_keys=True)


def test_t13_golden_file_has_250_cases_and_state_balance(record_property: pytest.RecordProperty) -> None:
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
    mixed = sum(1 for c in cases if c["expect"]["reason_code"] == "MIXED_OBJECTIVE_RESULTS")
    critical_or_missing = sum(
        1 for c in cases if c["expect"]["reason_code"] in {"CRITICAL_GATE_FAILED", "EVIDENCE_MISSING"}
    )
    assert mixed >= 30
    assert critical_or_missing >= 30
    assert "golden" not in {c["pack_slug"] for c in cases}
    assert not any("case_variant" in c["system"] for c in cases), "padding keys are not inputs"

    distinct: dict[str, set[str]] = {s: set() for s in states}
    controls: dict[str, set[str]] = {s: set() for s in states}
    for case in cases:
        state = case["expect"]["outcome_state"]
        distinct[state].add(_canonical_input(case))
        controls[state].add(case["control_key"])
    for state in sorted(states):
        record_property(f"t13_distinct_inputs_{state}", len(distinct[state]))
        record_property(f"t13_controls_{state}", len(controls[state]))
    record_property("t13_distinct_inputs_total", sum(len(v) for v in distinct.values()))
    record_property(
        "t13_unrelated_evidence_cases", sum(1 for c in cases if c["variation"] == "unrelated_evidence_added")
    )
    record_property("t13_expectation_source", "engine output checked against the selected state")


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
