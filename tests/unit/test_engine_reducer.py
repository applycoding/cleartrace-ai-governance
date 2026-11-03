from __future__ import annotations

from cleartrace_engine.evaluate import EvaluationInput, evaluate_control, objective_from_rule
from cleartrace_engine.reducer import reduce_outcome
from cleartrace_engine.types import ControlContext


def _control() -> ControlContext:
    return ControlContext(
        control_id="CA-DADM-APP-C-03",
        control_version="1.0.0",
        requirement_en="Peer review",
        requirement_fr="Examen par les pairs",
        clause_ref="Appendix C",
        source_url="https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592",
        remediation_en="Upload peer review.",
        remediation_fr="Téléverser l'examen par les pairs.",
    )


def test_critical_gate_beats_missing_evidence() -> None:
    state, reason = reduce_outcome(
        applicability_known=True,
        applicability=True,
        objective_results=[
            objective_from_rule(objective_key="peer", critical_gate=True, passed=False)
        ],
        evaluation_errors=[],
        evidence_issues=["EVIDENCE_MISSING"],
    )
    assert state.value == "not_met"
    assert reason == "CRITICAL_GATE_FAILED"


def test_evaluate_control_produces_bilingual_explanation() -> None:
    payload = EvaluationInput(
        contract_version="1.0",
        control=_control(),
        system={},
        evidence=[],
        metrics=[],
        applicability_known=True,
        applicability=True,
        objective_results=[
            objective_from_rule(objective_key="o1", critical_gate=False, passed=True)
        ],
        evaluation_errors=[],
        evidence_issues=[],
        engine_bundle_digest="deadbeef",
    )
    out = evaluate_control(payload)
    assert out.outcome_state == "met"
    assert "Exigence" in out.explanation_fr
    assert "Requirement" in out.explanation_en
