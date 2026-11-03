from __future__ import annotations

import json
from pathlib import Path

from cleartrace_engine.evaluate import (
    EvaluationInput,
    check_evidence,
    evaluate_control,
    objective_from_rule,
)
from cleartrace_engine.framework_studio import control_context_from_pack, load_pack

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests" / "fixtures" / "control_manifest.json"
PACKS = ROOT / "policies" / "packs"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _evaluate_seed(
    *,
    conformant: bool,
    missing: list[str],
    critical_gate: bool = True,
    control_key: str = "CA-DADM-APP-C-03",
) -> str:
    pack = load_pack(PACKS / "dadm" / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == control_key)
    ctx = control_context_from_pack(pack, control)
    evidence = []
    if conformant:
        evidence = [
            {
                "type": "peer_review_report",
                "authorized_submitter": True,
                "valid_until": "2099-01-01",
            }
        ]
    issues = check_evidence(evidence, [{"type": "peer_review_report", "required": True}])
    for miss in missing:
        if miss and miss not in issues:
            issues.append("EVIDENCE_MISSING")
    payload = EvaluationInput(
        contract_version="1.0",
        control=ctx,
        system={"planned_production_use": True, "impact_level": 3},
        evidence=evidence,
        metrics=[],
        applicability_known=True,
        applicability=True,
        objective_results=[
            objective_from_rule(
                objective_key="peer",
                critical_gate=critical_gate,
                passed=conformant and not missing,
            )
        ],
        evaluation_errors=[],
        evidence_issues=issues if missing else issues,
        engine_bundle_digest="test",
    )
    return evaluate_control(payload).outcome_state


def test_t08_non_conformities_detected() -> None:
    _load_manifest()
    cases = []
    for i in range(40):
        cases.append({"conformant": False, "missing": ["peer_review_report"]})
    for i in range(140):
        cases.append({"conformant": True, "missing": []})

    non_conf_found = 0
    false_not_met = 0
    explanation_pairs = 0
    for case in cases[:40]:
        state = _evaluate_seed(conformant=case["conformant"], missing=case["missing"])
        if state == "not_met":
            non_conf_found += 1
    for case in cases[40:]:
        state = _evaluate_seed(conformant=True, missing=[])
        if state == "met":
            explanation_pairs += 1
        if state == "not_met":
            false_not_met += 1

    assert non_conf_found == 40
    assert false_not_met == 0
    assert explanation_pairs >= 135
