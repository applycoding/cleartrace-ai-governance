#!/usr/bin/env python3
"""Generate 250 golden five-state cases for T-13 (50 per outcome state)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from cleartrace_engine.evaluate import EvaluationInput, evaluate_control, objective_from_rule
from cleartrace_engine.types import ControlContext

OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"


def base_control() -> ControlContext:
    return ControlContext(
        control_id="CA-TEST-01",
        control_version="1.0.0",
        requirement_en="Sample requirement",
        requirement_fr="Exigence d'exemple",
        clause_ref="TEST-1",
        source_url="https://example.ca/test",
        remediation_en="Provide evidence.",
        remediation_fr="Fournir une preuve.",
    )


def build_payload(**kwargs: object) -> EvaluationInput:
    return EvaluationInput(
        contract_version="1.0",
        control=base_control(),
        system={"planned_production_use": True},
        evidence=kwargs.get("evidence") or [],
        metrics=[],
        applicability_known=kwargs.get("applicability_known", True),
        applicability=kwargs.get("applicability", True),
        objective_results=kwargs.get("objective_results") or [],
        evaluation_errors=kwargs.get("evaluation_errors") or [],
        evidence_issues=kwargs.get("evidence_issues") or [],
        engine_bundle_digest="abc123",
    )


def expect_payload(payload: EvaluationInput) -> dict[str, str]:
    out = evaluate_control(payload)
    return {"outcome_state": out.outcome_state, "reason_code": out.reason_code}


def main() -> None:
    cases: list[dict[str, object]] = []

    for i in range(50):
        payload = build_payload(applicability=False)
        cases.append(
            {
                "id": f"na-{i}",
                "expect": expect_payload(payload),
                "payload": {"applicability": False},
            }
        )

    for i in range(50):
        payload = build_payload(
            objective_results=[
                objective_from_rule(objective_key=f"o{i}", critical_gate=False, passed=True)
            ]
        )
        cases.append({"id": f"met-{i}", "expect": expect_payload(payload)})

    for i in range(50):
        payload = build_payload(
            objective_results=[
                objective_from_rule(objective_key="pass", critical_gate=False, passed=True),
                objective_from_rule(objective_key="fail", critical_gate=False, passed=False),
            ]
        )
        cases.append({"id": f"pm-{i}", "expect": expect_payload(payload)})

    for i in range(20):
        payload = build_payload(
            objective_results=[
                objective_from_rule(objective_key="cg", critical_gate=False, passed=False)
            ]
        )
        cases.append({"id": f"nm-fail-{i}", "expect": expect_payload(payload)})

    for i in range(30):
        payload = build_payload(
            objective_results=[
                objective_from_rule(objective_key="cg", critical_gate=True, passed=False)
            ],
            evidence_issues=["EVIDENCE_MISSING"],
        )
        cases.append({"id": f"nm-critical-missing-{i}", "expect": expect_payload(payload)})

    for i in range(50):
        payload = build_payload(
            objective_results=[
                objective_from_rule(objective_key="ok", critical_gate=False, passed=True)
            ],
            evidence_issues=["EVIDENCE_MISSING"],
        )
        cases.append({"id": f"utd-missing-{i}", "expect": expect_payload(payload)})

    assert len(cases) == 250
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps([{"id": c["id"], "expect": c["expect"]} for c in cases], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(cases)} cases to {OUT}")


if __name__ == "__main__":
    main()
