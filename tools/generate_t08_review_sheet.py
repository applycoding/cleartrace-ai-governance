#!/usr/bin/env python3
"""Generate docs/trl5/t08_explanation_review.csv (140 EN/FR explanation pairs)."""

from __future__ import annotations

import csv
from pathlib import Path

from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control

ROOT = Path(__file__).resolve().parents[1]

OUT = ROOT / "docs" / "trl5" / "t08_explanation_review.csv"
PACK = ROOT / "policies" / "packs" / "dadm" / "pack.yaml"


def main() -> None:
    pack = load_pack(PACK)
    control = next(c for c in pack["controls"] if c["control_key"] == "CA-DADM-APP-C-03")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for i in range(140):
        system = {"planned_production_use": True, "impact_level": 3, "case_id": f"CONF-{i:03d}"}
        evidence = [
            {
                "type": "peer_review_report",
                "authorized_submitter": True,
                "valid_until": "2099-01-01",
            }
        ]
        output, ctx = assess_pack_control(
            pack=pack,
            control=control,
            system=system,
            evidence=evidence,
            pack_slug="dadm",
        )
        rows.append(
            {
                "case_id": f"CONF-{i:03d}",
                "control_key": control["control_key"],
                "clause_ref": control["clause_ref"],
                "source_url": pack["source_url_en"],
                "outcome_state": output.outcome_state,
                "explanation_en": output.explanation_en,
                "explanation_fr": output.explanation_fr,
                "reviewer_1_correct_yes_no": "",
                "reviewer_1_notes": "",
                "reviewer_2_correct_yes_no": "",
                "reviewer_2_notes": "",
            }
        )
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
