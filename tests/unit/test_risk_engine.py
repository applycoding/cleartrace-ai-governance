from __future__ import annotations

from cleartrace_risk.catalogue import STARTER_CATALOGUE
from cleartrace_risk.cel_evaluator import evaluate_cel
from cleartrace_risk.thresholds import classify_value
from cleartrace_risk.types import ObservationStatus


def test_starter_catalogue_covers_blueprint_areas() -> None:
    codes = {spec.code for spec in STARTER_CATALOGUE}
    assert "data.completeness.missing_rate" in codes
    assert "fairness.disparate_impact" in codes
    assert "safety.attack_success_rate" in codes
    assert len(STARTER_CATALOGUE) >= 12


def test_threshold_classification_higher_is_worse() -> None:
    assert classify_value(0.06, warn_value=0.02, breach_value=0.05, higher_is_worse=True) == (
        ObservationStatus.BREACH
    )


def test_cel_simple_expression() -> None:
    assert evaluate_cel("a + b > 3", {"a": 2, "b": 2}) is True
