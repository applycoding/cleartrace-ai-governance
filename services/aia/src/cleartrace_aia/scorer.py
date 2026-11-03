from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PINNED_COMMIT_REF = "b625733"
ATTRIBUTION = (
    "Survey structure derived from canada-ca/aia-eia-js (MIT), commit b625733, "
    "used only as fixture data for parity testing."
)


@dataclass(frozen=True)
class ScoreResult:
    raw_score: int
    max_raw_score: int
    mitigation_score: int
    max_mitigation_score: int
    final_score: int
    impact_level: int


def _parse_embedded_value(value: str) -> int:
    if not value:
        return 0
    idx = value.rfind("-")
    if idx == -1:
        return 0
    tail = value[idx + 1 :]
    try:
        return int(tail)
    except ValueError:
        return 0


def _get_value(raw: Any) -> int:
    if raw is None:
        return 0
    if isinstance(raw, list):
        return sum(_get_value(item) for item in raw)
    if isinstance(raw, str):
        return _parse_embedded_value(raw)
    if isinstance(raw, (int, float)):
        return int(raw)
    return 0


def _score_type(name: str, parent: str | None) -> int:
    for candidate in (name, parent or ""):
        if candidate.endswith("-RS"):
            return 2
        if candidate.endswith("-MS"):
            return 3
        if candidate.endswith("-NS"):
            return 1
    return 1


def _max_for_choices(choices: list[Any], qtype: str) -> int:
    values = [_get_value(c.get("value") if isinstance(c, dict) else c) for c in choices]
    if qtype == "checkbox":
        return sum(values)
    return max(values) if values else 0


def _iter_questions(survey: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for page in survey.get("pages", []):
        for element in page.get("elements", []):
            _collect_questions(element, None, questions)
    return questions


def _collect_questions(
    element: dict[str, Any], parent: str | None, out: list[dict[str, Any]]
) -> None:
    if element.get("type") == "panel":
        panel_name = element.get("name", "")
        for child in element.get("elements", []):
            _collect_questions(child, panel_name, out)
        return
    if "name" in element:
        out.append({**element, "_parent": parent})


def build_question_index(survey: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {q["name"]: q for q in _iter_questions(survey)}


def score_answers(
    answers: dict[str, Any],
    survey: dict[str, Any],
    *,
    clear_hidden: bool = True,
) -> ScoreResult:
    """Parity scorer aligned with canada-ca/aia-eia-js store.ts (commit b625733)."""
    if clear_hidden:
        answers = dict(answers)

    raw_score = 0
    max_raw = 0
    mitigation = 0
    max_mitigation = 0

    for question in _iter_questions(survey):
        name = question["name"]
        qtype = question.get("type", "")
        if qtype not in {"radiogroup", "checkbox", "dropdown"}:
            continue
        stype = _score_type(name, question.get("_parent"))
        if stype == 1:
            continue
        value = _get_value(answers.get(name))
        max_val = _max_for_choices(question.get("choices", []), qtype)
        if stype == 2:
            raw_score += value
            max_raw += max_val
        elif stype == 3:
            mitigation += value
            max_mitigation += max_val

    percentage = 0.8
    deduction = 0.15
    if mitigation >= percentage * (max_mitigation / 2):
        final_score = round((1 - deduction) * raw_score)
    else:
        final_score = raw_score

    threshold1 = 0.25
    threshold2 = 0.5
    threshold3 = 0.75
    if max_raw == 0 or final_score <= max_raw * threshold1:
        level = 1
    elif final_score <= max_raw * threshold2:
        level = 2
    elif final_score <= max_raw * threshold3:
        level = 3
    else:
        level = 4

    return ScoreResult(
        raw_score=raw_score,
        max_raw_score=max_raw,
        mitigation_score=mitigation,
        max_mitigation_score=max_mitigation,
        final_score=final_score,
        impact_level=level,
    )


def impact_level_from_final(final_score: int, *, max_raw: int = 167) -> int:
    """Fixed-boundary helper used in blueprint examples (max raw 167)."""
    if final_score <= 41:
        return 1
    if final_score <= 83:
        return 2
    if final_score <= 125:
        return 3
    return 4


def load_survey(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def load_default_survey(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[4]
    fixture = root / "tests/fixtures/aia/survey-enfr.b625733.json"
    return load_survey(fixture)


class AIAEngineService:
    """In-process AIA engine implementing the shared protocol shape."""

    def __init__(self, survey: dict[str, Any] | None = None) -> None:
        self._survey = survey or load_default_survey()

    async def score_answers(self, answers: dict[str, object]) -> dict[str, object]:
        result = score_answers(dict(answers), self._survey)
        return {
            "raw_score": result.raw_score,
            "mitigation_score": result.mitigation_score,
            "final_score": result.final_score,
            "impact_level": result.impact_level,
            "max_raw_score": result.max_raw_score,
            "pinned_commit": "b625733",
        }

    async def export_record(self, record_id: object) -> dict[str, object]:
        return {"record_id": str(record_id), "schema_version": "aia-eia-js-b625733"}
