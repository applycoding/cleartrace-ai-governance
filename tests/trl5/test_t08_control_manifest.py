from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control, finding_metadata
from tools.review_sheets import (
    T08_PASS_CORRECT,
    T08_TOTAL_PAIRS,
    t08_agreed_correct,
    t08_fill_state,
    t08_load_rows,
)

pytestmark = pytest.mark.usefixtures("opa_server")

ROOT = Path(__file__).resolve().parents[2]
AUTOMATED = ROOT / "tests" / "fixtures" / "t08_automated_cases.json"
PACKS = ROOT / "policies" / "packs"
REVIEW_SHEET = ROOT / "docs" / "trl5" / "t08_explanation_review.csv"


def _run_case(case: dict) -> str:
    pack = load_pack(PACKS / case["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == case["control_key"])
    output, _ = assess_pack_control(
        pack=pack,
        control=control,
        system=case["system"],
        evidence=case.get("evidence", []),
        pack_slug=case["pack_slug"],
        cel_context=case["system"],
    )
    return output.outcome_state


def test_t08_automated_non_conformities(record_property: pytest.RecordProperty) -> None:
    payload = json.loads(AUTOMATED.read_text(encoding="utf-8"))
    non_conf = payload["non_conformities"]
    conformant = payload["conformant"]
    assert len(non_conf) == 40
    assert len(conformant) == 40
    nc_ids = {c["id"] for c in non_conf}
    conf_ids = {c["id"] for c in conformant}
    assert len(nc_ids) == 40 and len(conf_ids) == 40
    assert not nc_ids & conf_ids
    for case in non_conf:
        assert _run_case(case) == "not_met"
    for case in conformant:
        assert _run_case(case) == "met"
    record_property("t08_nc_controls", len({c["control_key"] for c in non_conf}))
    record_property(
        "t08_nc_unrelated_evidence_cases", sum(1 for c in non_conf if c["variation"] == "unrelated_evidence_added")
    )
    record_property("t08_conformant_controls", len({c["control_key"] for c in conformant}))


def test_t08_human_explanation_review_sheet(record_property: pytest.RecordProperty) -> None:
    assert REVIEW_SHEET.exists(), "Run tools/generate_t08_cases.py"
    rows = t08_load_rows()
    assert len(rows) == T08_TOTAL_PAIRS
    case_ids = {row["case_id"] for row in rows}
    assert len(case_ids) == T08_TOTAL_PAIRS
    states = {row["outcome_state"] for row in rows}
    assert states == {
        "not_applicable",
        "met",
        "partially_met",
        "not_met",
        "unable_to_determine",
    }
    record_property("t08_distinct_explanations", len({(r["explanation_en"], r["explanation_fr"]) for r in rows}))
    fill = t08_fill_state(rows)
    if fill.state == "blank":
        pytest.xfail(
            f"Human review pending: {T08_TOTAL_PAIRS} EN/FR explanation pairs in "
            "docs/trl5/t08_explanation_review.csv await two reviewers (≥95% target)."
        )
    if fill.state == "partial":
        pytest.fail(f"T-08 review sheet partly filled: {fill.detail}")
    agreed = t08_agreed_correct(rows)
    assert agreed >= T08_PASS_CORRECT, (
        f"T-08 human gate: {agreed}/{T08_TOTAL_PAIRS} pairs marked correct by both reviewers; "
        f"need ≥{T08_PASS_CORRECT} (95%)."
    )


def test_t08_conformant_explanations_generated_via_opa() -> None:
    payload = json.loads(AUTOMATED.read_text(encoding="utf-8"))
    case = payload["conformant"][0]
    pack = load_pack(PACKS / case["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == case["control_key"])
    output, ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=case["system"],
        evidence=case.get("evidence", []),
        pack_slug=case["pack_slug"],
        cel_context=case["system"],
    )
    meta = finding_metadata(pack, control, ctx)
    assert output.outcome_state == "met"
    assert meta["clause_ref"]
    assert meta["source_url_en"].startswith("https://")
    assert output.explanation_en.strip()
    assert output.explanation_fr.strip()
