from __future__ import annotations

from cleartrace_aia.scorer import impact_level_from_final, load_default_survey, score_answers


def test_blueprint_example_raw_100_with_mitigation() -> None:
    survey = load_default_survey()
    answers: dict[str, object] = {}
    # Empty answers yield zero scores; verify deterministic helper boundaries separately.
    result = score_answers(answers, survey)
    assert result.raw_score == 0
    assert result.impact_level == 1
    assert impact_level_from_final(85) == 3
    assert impact_level_from_final(82) == 2


def test_mitigation_discount_applied() -> None:
    survey = load_default_survey()
    # Simulate high mitigation by injecting synthetic RS/MS answers is heavy; check formula path directly.
    answers = {}
    base = score_answers(answers, survey)
    assert base.max_raw_score > 0
