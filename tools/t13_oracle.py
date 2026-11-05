#!/usr/bin/env python3
"""Independent five-state oracle for T-13.

Expected outcomes are derived from the clause text of the shipped packs (DADM
Appendix C impact rows and the other pack clauses), not from OPA or the
assessment engine. The generator compares oracle output to the engine and keeps
only cases where they agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cleartrace_engine.evaluate import objective_from_rule
from cleartrace_engine.reducer import (
    REASON_APPLICABILITY_FALSE,
    reduce_outcome,
)
from cleartrace_engine.types import ObjectiveResult

# Multi-element evidence types and the elements each control requires by level.
# Derived from DADM Appendix C rows 1, 2, 4, 5, 6 and Level IV peer review.


@dataclass(frozen=True)
class _Spec:
    evidence_type: str
    critical: bool
    # None = single objective keyed by evidence_type; else callable(level)->elements
    elements_for_level: Any = None
    # applicability: "production" | "production_level_ge_N"
    apply: str = "production"


CONTROLS: dict[str, _Spec] = {
    # DADM critical single-evidence
    "CA-DADM-6-1-1": _Spec("aia_record", True),
    "CA-DADM-6-1-3": _Spec("aia_update_record", True),
    "CA-DADM-6-2-7": _Spec("decision_trace_record", True),
    "CA-DADM-6-3-1": _Spec("preprod_test_report", True),
    "CA-DADM-6-3-2": _Spec("monitoring_schedule_record", True),
    "CA-DADM-6-3-3": _Spec("human_rights_attestation", True),
    "CA-DADM-6-3-5": _Spec("dataset_validation_record", True),
    "CA-DADM-6-3-6": _Spec("data_governance_record", True),
    "CA-DADM-6-3-10": _Spec("security_risk_assessment", True),
    "CA-DADM-6-3-11": _Spec("integrity_controls_record", True),
    "CA-DADM-6-3-12": _Spec("legal_consultation_record", True),
    "CA-DADM-6-3-14": _Spec("operational_approval_record", True),
    "CA-DADM-6-4-1": _Spec("recourse_notice_record", True),
    "CA-DADM-6-5-1": _Spec("effectiveness_publication", True),
    "CA-DADM-6-5-2": _Spec("fairness_publication", True),
    # DADM multi-element / level-gated
    "CA-DADM-6-2-1": _Spec(
        "notice_record",
        False,
        elements_for_level=lambda lvl: (
            ["web", "in_person", "mail", "telephone", "explanation_link"]
            if lvl >= 3
            else ["web", "in_person", "mail", "telephone"]
        ),
    ),
    "CA-DADM-6-2-3": _Spec(
        "explanation_record",
        False,
        elements_for_level=lambda lvl: (
            ["general_public", "individualized_denial"] if lvl >= 2 else ["general_public"]
        ),
    ),
    "CA-DADM-6-3-7": _Spec(
        "peer_review_report",
        False,
        elements_for_level=lambda lvl: (
            ["expert_1", "expert_2"] if lvl >= 4 else (["peer_review"] if lvl >= 2 else [])
        ),
        apply="production_level_ge_2",
    ),
    "CA-DADM-APP-C-03": _Spec(
        "peer_review_report",
        True,
        elements_for_level=lambda lvl: (
            ["expert_1", "expert_2"] if lvl >= 4 else (["peer_review"] if lvl >= 3 else [])
        ),
        apply="production_level_ge_3",
    ),
    "CA-DADM-6-3-8": _Spec(
        "gba_plus_record",
        False,
        elements_for_level=lambda lvl: (
            ["population_impact_assessment", "di_experts_consulted", "mitigation_measures"]
            if lvl >= 2
            else []
        ),
        apply="production_level_ge_2",
    ),
    "CA-DADM-6-3-9": _Spec(
        "training_record",
        False,
        elements_for_level=lambda lvl: (
            ["technical", "privacy_fairness_rights", "evaluate_override"]
            if lvl >= 3
            else ["usage_explanation"]
        ),
    ),
    "CA-DADM-6-3-13": _Spec(
        "human_involvement_record",
        False,
        elements_for_level=lambda lvl: (
            ["final_human_decision", "qa_involvement"] if lvl >= 3 else ["qa_involvement"]
        ),
    ),
    # Other packs
    "CA-AIA-SCORE-01": _Spec("aia_record", True),
    "CA-PSD-4-1-28": _Spec("adm_accountability_record", True),
    "CA-PSD-4-1-26": _Spec("design_by_default_record", True),
    "CA-DSD-4-3-24": _Spec("canadian_facility_assessment", True),
    "CA-GC-AI-P4-REGISTER": _Spec("ai_register_entry", True),
    "CA-AI-PRIN-01": _Spec("principle_alignment_record", False),
    "CA-AI-PRIN-02": _Spec("principle_alignment_record", False),
    "CA-AI-PRIN-03": _Spec("principle_alignment_record", False),
    "CA-AI-PRIN-06": _Spec("principle_alignment_record", False),
    "CA-AI-PRIN-08": _Spec("principle_alignment_record", False),
    "CA-AI-PRIN-09": _Spec("principle_alignment_record", False),
    "NIST-AI-RMF-GV-1.1": _Spec("nist_govern_record", True),
    "ISO-42001-5-2": _Spec("iso_policy_record", True),
}

# Principle objective keys must match Rego (distinct per control).
_PRINCIPLE_KEYS = {
    "CA-AI-PRIN-01": "principle_1_impacts",
    "CA-AI-PRIN-02": "principle_2_transparency",
    "CA-AI-PRIN-03": "principle_3_explanations",
    "CA-AI-PRIN-06": "principle_6_human_rights",
    "CA-AI-PRIN-08": "principle_8_privacy_security",
    "CA-AI-PRIN-09": "principle_9_oversight",
}


def _valid(item: dict[str, Any], evidence_type: str) -> bool:
    return (
        item.get("type") == evidence_type
        and item.get("authorized_submitter") is True
        and item.get("valid_until") != "expired"
    )


def _covers(evidence: list[dict[str, Any]], evidence_type: str, element: str) -> bool:
    for item in evidence:
        if _valid(item, evidence_type) and element in (item.get("covers") or []):
            return True
    return False


def _has_valid(evidence: list[dict[str, Any]], evidence_type: str) -> bool:
    return any(_valid(item, evidence_type) for item in evidence)


def _evidence_issues(evidence: list[dict[str, Any]], evidence_type: str, required: bool) -> list[str]:
    """Match cleartrace.evidence issue ordering: missing first when no valid item."""
    issues: list[str] = []
    if required and not _has_valid(evidence, evidence_type):
        issues.append("EVIDENCE_MISSING")
    if any(
        item.get("type") == evidence_type and item.get("authorized_submitter") is False
        for item in evidence
    ):
        issues.append("SUBMITTER_UNAUTHORIZED")
    if any(
        item.get("type") == evidence_type and item.get("valid_until") == "expired"
        for item in evidence
    ):
        issues.append("EVIDENCE_STALE")
    return issues


def _applicable(spec: _Spec, system: dict[str, Any]) -> bool:
    if not system.get("planned_production_use"):
        return False
    level = int(system.get("impact_level") or 1)
    if spec.apply == "production_level_ge_2":
        return level >= 2
    if spec.apply == "production_level_ge_3":
        return level >= 3
    return True


def oracle_outcome(
    control_key: str, system: dict[str, Any], evidence: list[dict[str, Any]]
) -> tuple[str, str]:
    """Return (outcome_state, reason_code) from clause rules alone."""
    spec = CONTROLS.get(control_key)
    if spec is None:
        raise KeyError(f"no independent oracle rule for {control_key}")

    if not _applicable(spec, system):
        return "not_applicable", REASON_APPLICABILITY_FALSE

    level = int(system.get("impact_level") or 1)
    objectives: list[ObjectiveResult] = []

    if spec.elements_for_level is not None:
        elements = list(spec.elements_for_level(level))
        if not elements:
            return "not_applicable", REASON_APPLICABILITY_FALSE
        # Special case: Level II-III peer_review single key without covers list
        if elements == ["peer_review"]:
            passed = _has_valid(evidence, spec.evidence_type)
            objectives.append(
                objective_from_rule(
                    objective_key="peer_review",
                    applicable=True,
                    passed=passed,
                    critical_gate=spec.critical
                )
            )
        else:
            for element in elements:
                passed = _covers(evidence, spec.evidence_type, element)
                objectives.append(
                    objective_from_rule(
                        objective_key=element,
                        applicable=True,
                        passed=passed,
                        critical_gate=spec.critical
                    )
                )
    else:
        key = _PRINCIPLE_KEYS.get(control_key, spec.evidence_type)
        # Map known objective key aliases used in Rego
        aliases = {
            "aia_update_record": "aia_update",
            "decision_trace_record": "decision_trace",
            "preprod_test_report": "preprod_testing",
            "monitoring_schedule_record": "monitoring",
            "human_rights_attestation": "human_rights",
            "dataset_validation_record": "dataset_validation",
            "data_governance_record": "data_governance",
            "security_risk_assessment": "security_risk",
            "integrity_controls_record": "integrity",
            "legal_consultation_record": "legal_consult",
            "operational_approval_record": "operational_approval",
            "recourse_notice_record": "recourse",
            "effectiveness_publication": "effectiveness_pub",
            "fairness_publication": "fairness_pub",
            "aia_record": "aia_record" if control_key.startswith("CA-DADM") else "aia_score",
            "adm_accountability_record": "accountability",
            "design_by_default_record": "design_by_default",
            "canadian_facility_assessment": "canadian_facility",
            "ai_register_entry": "ai_register",
        }
        if control_key == "CA-AIA-SCORE-01":
            obj_key = "aia_score"
        elif control_key in _PRINCIPLE_KEYS:
            obj_key = _PRINCIPLE_KEYS[control_key]
        else:
            obj_key = aliases.get(spec.evidence_type, key)
        passed = _has_valid(evidence, spec.evidence_type)
        objectives.append(
            objective_from_rule(
                objective_key=obj_key,
                applicable=True,
                passed=passed,
                critical_gate=spec.critical
            )
        )

    # Required when the pack lists a required evidence_spec of this type.
    issues = _evidence_issues(evidence, spec.evidence_type, required=True)
    state, reason = reduce_outcome(
        applicability_known=True,
        applicability=True,
        objective_results=objectives,
        evaluation_errors=[],
        evidence_issues=issues,
    )
    return state.value, reason


def multi_element_types() -> dict[str, list[str]]:
    """Evidence types that use a covers list, with the union of possible elements."""
    return {
        "notice_record": ["web", "in_person", "mail", "telephone", "explanation_link"],
        "explanation_record": ["general_public", "individualized_denial"],
        "gba_plus_record": [
            "population_impact_assessment",
            "di_experts_consulted",
            "mitigation_measures",
        ],
        "training_record": [
            "usage_explanation",
            "technical",
            "privacy_fairness_rights",
            "evaluate_override",
        ],
        "human_involvement_record": ["qa_involvement", "final_human_decision"],
        "peer_review_report": ["expert_1", "expert_2"],
    }
