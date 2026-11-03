from __future__ import annotations

from cleartrace_engine.certainty import certainty_band, certainty_index_v0
from cleartrace_engine.evaluate import EvaluationInput, objective_from_rule
from cleartrace_engine.types import ControlContext


def _payload(**kwargs: object) -> EvaluationInput:
    return EvaluationInput(
        contract_version="1.0",
        control=ControlContext(
            control_id="CA-TEST",
            control_version="1.0.0",
            requirement_en="Req",
            requirement_fr="Exig",
            clause_ref="1",
            source_url="https://example.ca",
            remediation_en="Fix",
            remediation_fr="Corriger",
        ),
        system={},
        evidence=[],
        metrics=[],
        applicability_known=True,
        applicability=True,
        objective_results=kwargs.get("objective_results") or [],
        evaluation_errors=[],
        evidence_issues=kwargs.get("evidence_issues") or [],
        engine_bundle_digest="digest",
        used_llm=bool(kwargs.get("used_llm")),
    )


def test_t11_certainty_index_v0_is_uncalibrated_but_bounded() -> None:
    scores = []
    for passed in (True, False):
        for issue in ([], ["EVIDENCE_MISSING"], ["SUBMITTER_UNAUTHORIZED"]):
            payload = _payload(
                objective_results=[
                    objective_from_rule(objective_key="o", critical_gate=False, passed=passed)
                ],
                evidence_issues=issue,
            )
            score = certainty_index_v0(payload)
            scores.append(score)
            assert 0.0 <= score <= 1.0
            band_en, band_fr = certainty_band(score)
            assert band_en in {"high", "medium", "low"}
            assert band_fr in {"élevé", "moyen", "faible"}
    assert max(scores) >= 0.8
    assert min(scores) <= 0.5
    # Not claiming calibration; ECE gate intentionally not asserted here.
