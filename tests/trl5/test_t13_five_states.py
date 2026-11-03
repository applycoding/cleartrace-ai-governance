from __future__ import annotations

import json
from pathlib import Path

import pytest

from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"
GOLDEN_PACK = ROOT / "policies" / "packs" / "golden" / "pack.yaml"


def _scenario(case_id: str) -> str:
    if case_id.startswith("na-"):
        return "na"
    if case_id.startswith("met-"):
        return "met"
    if case_id.startswith("pm-"):
        return "pm"
    if case_id.startswith("nm-fail-"):
        return "nm_fail"
    if case_id.startswith("nm-critical-missing-"):
        return "nm_critical_missing"
    if case_id.startswith("utd-missing-"):
        return "utd_missing"
    raise AssertionError(f"Unknown case id {case_id}")


@pytest.fixture(scope="module")
def golden_pack() -> dict:
    return load_pack(GOLDEN_PACK)


@pytest.mark.parametrize("case", json.loads(GOLDEN.read_text(encoding="utf-8")))
def test_t13_golden_outcome(case: dict, golden_pack: dict) -> None:
    scenario = _scenario(case["id"])
    control = golden_pack["controls"][0]
    output, _ctx = assess_pack_control(
        pack=golden_pack,
        control=control,
        system={},
        evidence=[],
        pack_slug="golden",
        skip_cel=True,
        extra_opa_input={"scenario": scenario},
    )
    expect = case["expect"]
    assert output.outcome_state == expect["outcome_state"]
    assert output.reason_code == expect["reason_code"]


def test_t13_golden_file_has_250_cases() -> None:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(cases) == 250
