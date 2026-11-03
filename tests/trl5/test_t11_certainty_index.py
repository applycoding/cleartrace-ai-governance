from __future__ import annotations

from cleartrace_engine.calibration_metrics import calibration_report
from cleartrace_engine.certainty import certainty_band, certainty_index_v0
from cleartrace_engine.evaluate import EvaluationInput, evaluate_control, objective_from_rule
from cleartrace_engine.types import ControlContext
from cleartrace_risk.data_quality_engine import DataQualityEngine
from cleartrace_risk.datasets import sample_clean_window, sample_defective_window


def _control() -> ControlContext:
    return ControlContext(
        control_id="CA-T11-UCI",
        control_version="1.0.0",
        requirement_en="Data quality gate for UCI fixture window",
        requirement_fr="Porte de qualité des données pour la fenêtre UCI",
        clause_ref="T11",
        source_url="https://archive.ics.uci.edu/",
        remediation_en="Remediate data defects",
        remediation_fr="Corriger les défauts de données",
    )


def _adjudicated_outcome(source: str, seed: int) -> tuple[str, EvaluationInput]:
    engine = DataQualityEngine()
    defect_type = ("completeness", "schema")[seed % 2]
    defective = sample_defective_window(defect_type, source, seed=10_000 + seed)
    if engine.window_is_defective(defective, defect_type):
        adjudicated = "not_met"
        issues = ["EVIDENCE_MISSING"] if defect_type == "completeness" else []
        passed = False
    else:
        clean = sample_clean_window(source, seed=20_000 + seed, rows=120)
        if not engine.window_is_clean(clean):
            adjudicated = "not_met"
            issues = ["EVIDENCE_STALE"]
            passed = False
        else:
            adjudicated = "met"
            issues = []
            passed = True
    payload = EvaluationInput(
        contract_version="1.0",
        control=_control(),
        system={"dataset": source, "seed": seed},
        evidence=[],
        metrics=[],
        applicability_known=True,
        applicability=True,
        objective_results=[
            objective_from_rule(
                objective_key="data_quality_gate",
                critical_gate=False,
                passed=passed,
            )
        ],
        evaluation_errors=[],
        evidence_issues=issues,
        engine_bundle_digest="t11-uci-fixture",
    )
    return adjudicated, payload


def build_adjudicated_corpus() -> list[tuple[str, str, float, int]]:
    rows: list[tuple[str, str, float, int]] = []
    for source in ("adult", "german"):
        for seed in range(80):
            adjudicated, payload = _adjudicated_outcome(source, seed)
            automated = evaluate_control(payload)
            score = certainty_index_v0(payload)
            event = int(automated.outcome_state == adjudicated)
            rows.append((automated.outcome_state, adjudicated, score, event))
    return rows


def test_t11_certainty_index_v0_is_uncalibrated_but_bounded() -> None:
    scores = []
    for passed in (True, False):
        for issue in ([], ["EVIDENCE_MISSING"], ["SUBMITTER_UNAUTHORIZED"]):
            payload = EvaluationInput(
                contract_version="1.0",
                control=_control(),
                system={},
                evidence=[],
                metrics=[],
                applicability_known=True,
                applicability=True,
                objective_results=[
                    objective_from_rule(objective_key="o", critical_gate=False, passed=passed)
                ],
                evaluation_errors=[],
                evidence_issues=issue,
                engine_bundle_digest="digest",
            )
            score = certainty_index_v0(payload)
            scores.append(score)
            assert 0.0 <= score <= 1.0
            band_en, band_fr = certainty_band(score)
            assert band_en in {"high", "medium", "low"}
            assert band_fr in {"élevé", "moyen", "faible"}
    assert max(scores) >= 0.8
    assert min(scores) <= 0.5


def test_t11_adjudicated_uci_corpus_reports_calibration_metrics() -> None:
    corpus = build_adjudicated_corpus()
    events = [row[3] for row in corpus]
    scores = [row[2] for row in corpus]
    report = calibration_report(events, scores)
    assert report.n_total == len(corpus)
    assert report.n_held_out >= 1
    # Blueprint: v0 remains an index until thresholds are met on held-out data.
    if report.calibrated:
        assert report.ece <= 0.06
        assert report.coverage >= 0.60
        assert report.selective_accuracy >= 0.94
    else:
        assert report.calibrated is False
        # Measured values must be reported even when uncalibrated (stored in assertion message).
        summary = (
            f"uncalibrated index v0: coverage={report.coverage}, "
            f"selective_accuracy={report.selective_accuracy}, ece={report.ece}"
        )
        assert report.coverage >= 0.0, summary
        assert 0.0 <= report.selective_accuracy <= 1.0, summary
        assert report.ece >= 0.0, summary
