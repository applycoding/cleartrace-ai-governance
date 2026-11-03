from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleartrace_engine.evaluate import EvaluationInput, evaluate_control, objective_from_rule
from cleartrace_engine.types import ControlContext

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"


def _control() -> ControlContext:
    return ControlContext(
        control_id="CA-TEST-01",
        control_version="1.0.0",
        requirement_en="Sample requirement",
        requirement_fr="Exigence d'exemple",
        clause_ref="TEST-1",
        source_url="https://example.ca/test",
        remediation_en="Provide evidence.",
        remediation_fr="Fournir une preuve.",
    )


@pytest.mark.parametrize("case", json.loads(GOLDEN.read_text(encoding="utf-8")))
def test_t13_golden_outcome(case: dict) -> None:
    expect = case["expect"]
    case_id = case["id"]
    if case_id.startswith("na-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=False,
            objective_results=[],
            evaluation_errors=[],
            evidence_issues=[],
            engine_bundle_digest="abc123",
        )
    elif case_id.startswith("met-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=True,
            objective_results=[
                objective_from_rule(objective_key="o", critical_gate=False, passed=True)
            ],
            evaluation_errors=[],
            evidence_issues=[],
            engine_bundle_digest="abc123",
        )
    elif case_id.startswith("pm-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=True,
            objective_results=[
                objective_from_rule(objective_key="pass", critical_gate=False, passed=True),
                objective_from_rule(objective_key="fail", critical_gate=False, passed=False),
            ],
            evaluation_errors=[],
            evidence_issues=[],
            engine_bundle_digest="abc123",
        )
    elif case_id.startswith("nm-fail-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=True,
            objective_results=[
                objective_from_rule(objective_key="cg", critical_gate=False, passed=False)
            ],
            evaluation_errors=[],
            evidence_issues=[],
            engine_bundle_digest="abc123",
        )
    elif case_id.startswith("nm-critical-missing-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=True,
            objective_results=[
                objective_from_rule(objective_key="cg", critical_gate=True, passed=False)
            ],
            evaluation_errors=[],
            evidence_issues=["EVIDENCE_MISSING"],
            engine_bundle_digest="abc123",
        )
    elif case_id.startswith("utd-missing-"):
        payload = EvaluationInput(
            contract_version="1.0",
            control=_control(),
            system={},
            evidence=[],
            metrics=[],
            applicability_known=True,
            applicability=True,
            objective_results=[
                objective_from_rule(objective_key="ok", critical_gate=False, passed=True)
            ],
            evaluation_errors=[],
            evidence_issues=["EVIDENCE_MISSING"],
            engine_bundle_digest="abc123",
        )
    else:
        pytest.fail(f"Unknown golden case id {case_id}")

    out = evaluate_control(payload)
    assert out.outcome_state == expect["outcome_state"]
    assert out.reason_code == expect["reason_code"]


def test_t13_golden_file_has_250_cases() -> None:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(cases) == 250
