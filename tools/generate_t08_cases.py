#!/usr/bin/env python3
"""Generate T-08 automated cases and the 140-pair human explanation review sheet.

Cases come from the same enumeration of shipped controls as the T-13 golden set
(tools/generate_t13_golden.py), with expected states from the independent clause
oracle. Reviewer columns are written blank.
"""


from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from tools.generate_t13_golden import STATES, select_cases  # noqa: E402

AUTOMATED_OUT = ROOT / "tests" / "fixtures" / "t08_automated_cases.json"
REVIEW_OUT = ROOT / "docs" / "trl5" / "t08_explanation_review.csv"
PER_STATE_REVIEW = 28
_PREFIX = {
    "not_applicable": "NA",
    "met": "MET",
    "partially_met": "PM",
    "not_met": "NM",
    "unable_to_determine": "UTD",
}


def input_summary(system: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    parts = [
        f"production use: {'yes' if system.get('planned_production_use') else 'no'}",
        f"impact level: {system.get('impact_level', '-')}",
    ]
    if not evidence:
        parts.append("evidence: none")
    for item in evidence:
        state = "authorised" if item.get("authorized_submitter") else "unauthorised submitter"
        valid = "expired" if item.get("valid_until") == "expired" else f"valid until {item.get('valid_until')}"
        text = f"evidence: {item['type']} ({state}, {valid}"
        if "covers" in item:
            text += f", covers: {', '.join(item['covers']) or 'none'}"
        parts.append(text + ")")
    return "; ".join(parts)


def _case(item: dict[str, Any], case_id: str) -> dict[str, Any]:
    return {
        "id": case_id,
        "pack_slug": item["pack"]["slug"],
        "control_key": item["control"]["control_key"],
        "variation": item["variation"],
        "system": item["system"],
        "evidence": item["evidence"],
        "expect": {"outcome_state": item["output"].outcome_state},
    }


def build_automated() -> dict[str, list[dict[str, Any]]]:
    return {
        "non_conformities": [_case(c, f"NC-{i:03d}") for i, c in enumerate(select_cases("not_met", 40))],
        "conformant": [_case(c, f"CONF-{i:03d}") for i, c in enumerate(select_cases("met", 40))],
    }


def build_review_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for state in STATES:
        for idx, item in enumerate(select_cases(state, PER_STATE_REVIEW)):
            output = item["output"]
            control = item["control"]
            rows.append(
                {
                    "case_id": f"{_PREFIX[state]}-{idx:03d}",
                    "pack_slug": str(item["pack"]["slug"]),
                    "control_key": str(control["control_key"]),
                    "clause_ref": str(control.get("clause_ref", "")),
                    "source_url": str(item["pack"]["source_url_en"]),
                    "input_summary": input_summary(item["system"], item["evidence"]),
                    "variation": str(item["variation"]),
                    "outcome_state": output.outcome_state,
                    "explanation_en": output.explanation_en,
                    "explanation_fr": output.explanation_fr,
                    "reviewer_1_correct_yes_no": "",
                    "reviewer_1_notes": "",
                    "reviewer_2_correct_yes_no": "",
                    "reviewer_2_notes": "",
                }
            )
    if len(rows) != 140 or len({r["case_id"] for r in rows}) != 140:
        raise RuntimeError("expected 140 distinct review rows")
    return rows


def main() -> None:
    AUTOMATED_OUT.write_text(json.dumps(build_automated(), indent=2) + "\n", encoding="utf-8")
    rows = build_review_rows()
    with REVIEW_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {AUTOMATED_OUT} and {len(rows)} review rows to {REVIEW_OUT}")


if __name__ == "__main__":
    main()
