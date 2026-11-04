"""Distinct shipped-pack evaluation profiles for TRL 5 generators (T-08, T-13)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "policies" / "packs"

SHIPPED_SLUGS = (
    "dadm",
    "aia",
    "psd",
    "dsd",
    "ai-strategy",
    "guiding-principles",
    "nist-ai-rmf",
    "iso42001-ids",
)

_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "aia_record": {"type": "aia_record", "authorized_submitter": True, "valid_until": "2099-06-01"},
    "peer_review_report": {
        "type": "peer_review_report",
        "authorized_submitter": True,
        "valid_until": "2099-06-02",
    },
    "adm_accountability_record": {
        "type": "adm_accountability_record",
        "authorized_submitter": True,
        "valid_until": "2099-06-03",
    },
    "design_by_default_record": {
        "type": "design_by_default_record",
        "authorized_submitter": True,
        "valid_until": "2099-06-04",
    },
    "canadian_facility_assessment": {
        "type": "canadian_facility_assessment",
        "authorized_submitter": True,
        "valid_until": "2099-06-05",
    },
    "ai_register_entry": {
        "type": "ai_register_entry",
        "authorized_submitter": True,
        "valid_until": "2099-06-06",
    },
    "principle_alignment_record": {
        "type": "principle_alignment_record",
        "authorized_submitter": True,
        "valid_until": "2099-06-07",
    },
}


def evidence(*keys: str, suffix: int = 0) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for key in keys:
        base = dict(_VALID_EVIDENCE[key])
        base["valid_until"] = f"2099-06-{10 + (suffix % 18):02d}"
        items.append(base)
    return items


def bad_evidence(
    evidence_type: str,
    *,
    unauthorized: bool = False,
    stale: bool = False,
) -> list[dict[str, object]]:
    item: dict[str, object] = {
        "type": evidence_type,
        "authorized_submitter": not unauthorized,
        "valid_until": "expired" if stale else "2099-01-01",
    }
    return [item]


def profile_templates(target_state: str) -> list[tuple[str, str, dict[str, object], list[dict[str, object]]]]:
    prod: dict[str, object] = {"planned_production_use": True}
    idle: dict[str, object] = {"planned_production_use": False}
    if target_state == "not_applicable":
        return [
            ("dadm", "CA-DADM-6-1-1", {**idle, "impact_level": 2}, []),
            ("dadm", "CA-DADM-6-3-7", {**idle, "impact_level": 2}, []),
            ("dadm", "CA-DADM-APP-C-03", {**idle, "impact_level": 3}, []),
            ("aia", "CA-AIA-SCORE-01", idle, []),
            ("psd", "CA-PSD-4-1-28", idle, []),
            ("psd", "CA-PSD-4-1-26", idle, []),
            ("dsd", "CA-DSD-4-3-24", idle, []),
            ("ai-strategy", "CA-GC-AI-P4-REGISTER", idle, []),
            ("guiding-principles", "CA-AI-PRIN-01", idle, []),
            ("guiding-principles", "CA-AI-PRIN-02", idle, []),
            ("nist-ai-rmf", "NIST-AI-RMF-GV-1.1", idle, []),
            ("iso42001-ids", "ISO-42001-AI-POLICY", idle, []),
        ]
    if target_state == "met":
        return [
            ("dadm", "CA-DADM-6-1-1", {**prod, "impact_level": 2}, evidence("aia_record")),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, evidence("peer_review_report", "aia_record")),
            ("dadm", "CA-DADM-APP-C-03", {**prod, "impact_level": 3}, evidence("peer_review_report")),
            ("aia", "CA-AIA-SCORE-01", prod, evidence("aia_record")),
            ("psd", "CA-PSD-4-1-28", prod, evidence("adm_accountability_record")),
            ("psd", "CA-PSD-4-1-26", prod, evidence("design_by_default_record")),
            ("dsd", "CA-DSD-4-3-24", prod, evidence("canadian_facility_assessment")),
            ("ai-strategy", "CA-GC-AI-P4-REGISTER", prod, evidence("ai_register_entry")),
            ("guiding-principles", "CA-AI-PRIN-01", prod, evidence("principle_alignment_record")),
            ("guiding-principles", "CA-AI-PRIN-02", prod, evidence("principle_alignment_record")),
            ("nist-ai-rmf", "NIST-AI-RMF-GV-1.1", prod, []),
            ("iso42001-ids", "ISO-42001-AI-POLICY", prod, []),
        ]
    if target_state == "partially_met":
        return [
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, evidence("aia_record")),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 3}, evidence("peer_review_report")),
        ]
    if target_state == "not_met":
        return [
            ("dadm", "CA-DADM-APP-C-03", {**prod, "impact_level": 3}, []),
            ("dadm", "CA-DADM-6-1-1", {**prod, "impact_level": 2}, []),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, []),
        ]
    if target_state == "unable_to_determine":
        return [
            ("aia", "CA-AIA-SCORE-01", prod, bad_evidence("aia_record", unauthorized=True)),
            ("psd", "CA-PSD-4-1-26", prod, bad_evidence("design_by_default_record", stale=True)),
            ("psd", "CA-PSD-4-1-28", prod, bad_evidence("adm_accountability_record", unauthorized=True)),
            ("guiding-principles", "CA-AI-PRIN-01", prod, bad_evidence("principle_alignment_record", stale=True)),
            ("dsd", "CA-DSD-4-3-24", prod, bad_evidence("canadian_facility_assessment", unauthorized=True)),
        ]
    raise ValueError(f"unknown target_state {target_state}")


def expand_distinct_cases(
    target_state: str,
    count: int,
    *,
    id_prefix: str,
) -> list[dict[str, Any]]:
    templates = profile_templates(target_state)
    cases: list[dict[str, Any]] = []
    idx = 0
    while len(cases) < count:
        pack_slug, control_key, system, ev = templates[idx % len(templates)]
        variant = len(cases)
        system_v = dict(system)
        system_v["profile_variant"] = variant
        system_v["case_id"] = f"{id_prefix}-{variant:03d}"
        if "impact_level" in system_v:
            system_v["impact_level"] = int(system_v["impact_level"]) + (variant % 3)
        evidence_v: list[dict[str, object]]
        if not ev:
            evidence_v = []
        elif any(
            item.get("authorized_submitter") is False or item.get("valid_until") == "expired"
            for item in ev
        ):
            evidence_v = [dict(item) for item in ev]
        else:
            evidence_v = evidence(
                *[str(item["type"]) for item in ev],
                suffix=variant,
            )
        cases.append(
            {
                "id": system_v["case_id"],
                "pack_slug": pack_slug,
                "control_key": control_key,
                "system": system_v,
                "evidence": evidence_v,
                "target_state": target_state,
            }
        )
        idx += 1
    return cases
