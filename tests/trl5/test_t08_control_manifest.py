from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cleartrace_engine.framework_studio import load_pack
from cleartrace_engine.pipeline import assess_pack_control, finding_metadata

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests" / "fixtures" / "control_manifest.json"
PACKS = ROOT / "policies" / "packs"
REVIEW_SHEET = ROOT / "docs" / "trl5" / "t08_explanation_review.csv"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_t08_automated_non_conformities() -> None:
    _load_manifest()
    pack = load_pack(PACKS / "dadm" / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == "CA-DADM-APP-C-03")
    non_conf_found = 0
    false_not_met = 0
    for _i in range(40):
        output, _ = assess_pack_control(
            pack=pack,
            control=control,
            system={"planned_production_use": True, "impact_level": 3},
            evidence=[],
            pack_slug="dadm",
        )
        if output.outcome_state == "not_met":
            non_conf_found += 1
    for _i in range(40):
        output, _ = assess_pack_control(
            pack=pack,
            control=control,
            system={"planned_production_use": True, "impact_level": 1},
            evidence=[],
            pack_slug="dadm",
        )
        if output.outcome_state == "not_met":
            false_not_met += 1
    assert non_conf_found == 40
    assert false_not_met == 0


def test_t08_human_explanation_review_pending() -> None:
    assert REVIEW_SHEET.exists(), "Run tools/generate_t08_review_sheet.py"
    with REVIEW_SHEET.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 140
    pending = [
        r
        for r in rows
        if not r.get("reviewer_1_correct_yes_no") or not r.get("reviewer_2_correct_yes_no")
    ]
    assert len(pending) == 140
    pytest.xfail(
        "Human review pending: 140 EN/FR explanation pairs in "
        "docs/trl5/t08_explanation_review.csv await two reviewers (≥95% target)."
    )


def test_t08_conformant_explanations_generated_via_opa() -> None:
    pack = load_pack(PACKS / "dadm" / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == "CA-DADM-APP-C-03")
    output, ctx = assess_pack_control(
        pack=pack,
        control=control,
        system={"planned_production_use": True, "impact_level": 3},
        evidence=[
            {
                "type": "peer_review_report",
                "authorized_submitter": True,
                "valid_until": "2099-01-01",
            }
        ],
        pack_slug="dadm",
    )
    meta = finding_metadata(pack, control, ctx)
    assert output.outcome_state == "met"
    assert meta["clause_ref"]
    assert meta["source_url_en"].startswith("https://")
