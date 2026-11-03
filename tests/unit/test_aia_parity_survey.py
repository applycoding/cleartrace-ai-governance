from __future__ import annotations

from cleartrace_aia.scorer import load_default_survey, score_answers


def test_survey_max_raw_score_is_167() -> None:
    survey = load_default_survey()
    result = score_answers({}, survey)
    assert result.max_raw_score == 167
    assert result.raw_score == 0
    assert result.impact_level == 1
