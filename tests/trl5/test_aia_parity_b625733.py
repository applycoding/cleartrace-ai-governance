from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from cleartrace_aia.scorer import load_default_survey, score_answers

ROOT = Path(__file__).resolve().parents[2]
NODE_SCRIPT = ROOT / "tests" / "fixtures" / "aia" / "official_score_b625733.mjs"
SURVEY = ROOT / "tests" / "fixtures" / "aia" / "survey-enfr.b625733.json"
PARITY_SETS = ROOT / "tests" / "fixtures" / "aia" / "parity_answer_sets.json"
PUBLISHED = [
    ROOT / "tests/fixtures/aia/published/ircc-aast-aia-results.json",
    ROOT / "tests/fixtures/aia/published/cbsa-cres-aia-results.json",
    ROOT / "tests/fixtures/aia/published/cbsa-srec-aia-results.json",
]


def _node_score(answers: dict[str, object]) -> dict[str, int]:
    env = os.environ.copy()
    env["AIA_SURVEY_PATH"] = str(SURVEY)
    proc = subprocess.run(
        ["node", str(NODE_SCRIPT)],
        input=json.dumps(answers),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return json.loads(proc.stdout)


def _extract_answers_from_published(payload: dict) -> dict[str, object]:
    if "answers" in payload and isinstance(payload["answers"], dict):
        return payload["answers"]
    if "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    if "toolData" in payload and isinstance(payload["toolData"], dict):
        return payload["toolData"]
    return {}


@pytest.fixture(scope="module")
def survey() -> dict:
    return load_default_survey()


def test_aia_parity_set_matches_node(survey: dict) -> None:
    cases = json.loads(PARITY_SETS.read_text(encoding="utf-8"))
    assert len(cases) >= 200
    mismatches = 0
    for case in cases:
        answers = dict(case["answers"])
        py = score_answers(answers, survey)
        node = _node_score(answers)
        if (
            py.raw_score != node["raw_score"]
            or py.mitigation_score != node["mitigation_score"]
            or py.impact_level != node["impact_level"]
        ):
            mismatches += 1
    assert mismatches == 0, f"{mismatches} parity mismatches"


@pytest.mark.parametrize("path", PUBLISHED)
def test_published_aia_exports_score(path: Path, survey: dict) -> None:
    if not path.exists():
        pytest.skip(f"Published fixture missing: {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    answers = _extract_answers_from_published(payload)
    if not answers:
        pytest.skip("No answers map in published export")
    py = score_answers(answers, survey)
    node = _node_score(answers)
    assert py.raw_score == node["raw_score"]
    assert py.mitigation_score == node["mitigation_score"]
    assert py.impact_level == node["impact_level"]
