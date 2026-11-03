#!/usr/bin/env python3
"""Generate >=200 random AIA parity answer sets using real survey choice values."""

from __future__ import annotations

import json
import random
from pathlib import Path

from cleartrace_aia.scorer import build_question_index, load_default_survey, score_answers

ROOT = Path(__file__).resolve().parents[1]

OUT = ROOT / "tests" / "fixtures" / "aia" / "parity_answer_sets.json"


def main() -> None:
    survey = load_default_survey()
    index = build_question_index(survey)
    scored_names = [
        n
        for n, q in index.items()
        if q.get("type") in {"radiogroup", "checkbox", "dropdown"}
        and (n.endswith("-RS") or n.endswith("-MS") or (q.get("_parent") or "").endswith("-RS"))
    ]
    rng = random.Random(20261103)
    cases: list[dict[str, object]] = [{"id": "empty", "answers": {}}]
    for i in range(229):
        answers: dict[str, object] = {}
        for name in rng.sample(scored_names, k=min(8, len(scored_names))):
            q = index[name]
            choices = q.get("choices") or []
            if not choices:
                continue
            choice = rng.choice(choices)
            answers[name] = choice.get("value", choice)
        cases.append({"id": f"set-{i:03d}", "answers": answers})
    for case in cases:
        score_answers(dict(case["answers"]), survey)
    OUT.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(len(cases), "cases ->", OUT)


if __name__ == "__main__":
    main()
