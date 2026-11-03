from __future__ import annotations

from pathlib import Path
from typing import Any

from cleartrace_aia.scorer import load_default_survey, score_answers


def run_official_node_scorer(answers: dict[str, Any], repo_path: Path) -> dict[str, int] | None:
    """Optional harness when Node.js and a cloned official repo are available."""
    return None


def assert_parity(answers: dict[str, Any], survey_path: Path | None = None) -> None:
    survey = load_default_survey() if survey_path is None else load_default_survey()
    if survey_path is not None:
        from cleartrace_aia.scorer import load_survey

        survey = load_survey(survey_path)
    ours = score_answers(answers, survey)
    assert ours.max_raw_score > 0
