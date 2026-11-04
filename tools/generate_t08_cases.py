#!/usr/bin/env python3
"""Generate T-08 automated cases and the 140-pair human explanation review sheet."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from cleartrace_engine.framework_studio import load_pack  # noqa: E402
from cleartrace_engine.pipeline import assess_pack_control  # noqa: E402
from tools.shipped_eval_profiles import expand_distinct_cases  # noqa: E402

AUTOMATED_OUT = ROOT / "tests" / "fixtures" / "t08_automated_cases.json"
REVIEW_OUT = ROOT / "docs" / "trl5" / "t08_explanation_review.csv"
PACKS = ROOT / "policies" / "packs"


def _assess_case(case: dict) -> dict:
    pack = load_pack(PACKS / case["pack_slug"] / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == case["control_key"])
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=case["system"],
        evidence=case.get("evidence", []),
        pack_slug=case["pack_slug"],
        cel_context=case["system"],
    )
    return {
        "outcome_state": output.outcome_state,
        "reason_code": output.reason_code,
        "explanation_en": output.explanation_en,
        "explanation_fr": output.explanation_fr,
        "clause_ref": control.get("clause_ref", ""),
        "source_url": pack["source_url_en"],
    }


def _build_automated() -> dict:
    non_conf = expand_distinct_cases("not_met", 40, id_prefix="NC")
    conformant = expand_distinct_cases("met", 40, id_prefix="CONF")
    for bucket in (non_conf, conformant):
        for case in bucket:
            result = _assess_case(case)
            expect = "not_met" if bucket is non_conf else "met"
            if result["outcome_state"] != expect:
                raise RuntimeError(
                    f"{case['id']} expected {expect}, got {result['outcome_state']} "
                    f"on {case['pack_slug']}/{case['control_key']}"
                )
            case["expect"] = {"outcome_state": result["outcome_state"]}
    return {"non_conformities": non_conf, "conformant": conformant}


def _build_review_rows() -> list[dict[str, str]]:
    per_state = 28
    rows: list[dict[str, str]] = []
    state_prefix = {
        "not_applicable": "NA",
        "met": "MET",
        "partially_met": "PM",
        "not_met": "NM",
        "unable_to_determine": "UTD",
    }
    for state in (
        "not_applicable",
        "met",
        "partially_met",
        "not_met",
        "unable_to_determine",
    ):
        cases = expand_distinct_cases(state, per_state, id_prefix=state_prefix[state])
        for case in cases:
            result = _assess_case(case)
            if result["outcome_state"] != state:
                raise RuntimeError(
                    f"Review {case['id']} wanted {state}, got {result['outcome_state']}"
                )
            rows.append(
                {
                    "case_id": case["id"],
                    "pack_slug": case["pack_slug"],
                    "control_key": case["control_key"],
                    "clause_ref": result["clause_ref"],
                    "source_url": result["source_url"],
                    "outcome_state": result["outcome_state"],
                    "explanation_en": result["explanation_en"],
                    "explanation_fr": result["explanation_fr"],
                    "reviewer_1_correct_yes_no": "",
                    "reviewer_1_notes": "",
                    "reviewer_2_correct_yes_no": "",
                    "reviewer_2_notes": "",
                }
            )
    if len(rows) != 140:
        raise RuntimeError(f"expected 140 review rows, got {len(rows)}")
    ids = {row["case_id"] for row in rows}
    if len(ids) != 140:
        raise RuntimeError("review sheet case_id values must be distinct")
    return rows


def main() -> None:
    automated = _build_automated()
    AUTOMATED_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUTOMATED_OUT.write_text(json.dumps(automated, indent=2), encoding="utf-8")
    review_rows = _build_review_rows()
    REVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0].keys()))
        writer.writeheader()
        writer.writerows(review_rows)
    print(f"Wrote automated cases to {AUTOMATED_OUT}")
    print(f"Wrote {len(review_rows)} explanation pairs to {REVIEW_OUT}")


if __name__ == "__main__":
    main()
