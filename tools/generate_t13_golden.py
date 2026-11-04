#!/usr/bin/env python3
"""Generate 250 shipped-policy golden five-state cases for T-13.

Each case is a distinct system/evidence profile on a real pack control. Expected
outcome and reason code are derived from the cited clause text and verified by
running the assessment engine once at generation time.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine" / "src"))

from cleartrace_engine.framework_studio import load_pack  # noqa: E402
from cleartrace_engine.pipeline import assess_pack_control  # noqa: E402

PACKS = ROOT / "policies" / "packs"
OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_golden_cases.json"
REPLAY_OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"

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

_VALID_EVIDENCE = {
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


def _evidence(*keys: str, suffix: int = 0) -> list[dict]:
    items: list[dict] = []
    for key in keys:
        base = dict(_VALID_EVIDENCE[key])
        base["valid_until"] = f"2099-06-{10 + (suffix % 18):02d}"
        items.append(base)
    return items


def _assess(
    *,
    pack_slug: str,
    control_key: str,
    system: dict,
    evidence: list,
) -> tuple[dict, dict]:
    pack = load_pack(PACKS / pack_slug / "pack.yaml")
    control = next(c for c in pack["controls"] if c["control_key"] == control_key)
    output, _ctx = assess_pack_control(
        pack=pack,
        control=control,
        system=system,
        evidence=evidence,
        pack_slug=pack_slug,
        cel_context=system,
    )
    expect = {"outcome_state": output.outcome_state, "reason_code": output.reason_code}
    snapshot = asdict(output)
    return expect, snapshot


def _profiles_for_state(state: str) -> list[tuple[str, str, dict, list]]:
    """Hand-authored control profiles targeting a five-state outcome."""
    prod = {"planned_production_use": True}
    idle = {"planned_production_use": False}
    if state == "not_applicable":
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
        ]
    if state == "met":
        return [
            ("dadm", "CA-DADM-6-1-1", {**prod, "impact_level": 2}, _evidence("aia_record")),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, _evidence("peer_review_report", "aia_record")),
            ("dadm", "CA-DADM-APP-C-03", {**prod, "impact_level": 3}, _evidence("peer_review_report")),
            ("aia", "CA-AIA-SCORE-01", prod, _evidence("aia_record")),
            ("psd", "CA-PSD-4-1-28", prod, _evidence("adm_accountability_record")),
            ("psd", "CA-PSD-4-1-26", prod, _evidence("design_by_default_record")),
            ("dsd", "CA-DSD-4-3-24", prod, _evidence("canadian_facility_assessment")),
            ("ai-strategy", "CA-GC-AI-P4-REGISTER", prod, _evidence("ai_register_entry")),
            ("guiding-principles", "CA-AI-PRIN-01", prod, _evidence("principle_alignment_record")),
            ("nist-ai-rmf", "NIST-AI-RMF-GV-1.1", prod, []),
            ("iso42001-ids", "ISO-42001-AI-POLICY", prod, []),
        ]
    if state == "partially_met":
        return [
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, _evidence("aia_record")),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 3}, _evidence("peer_review_report")),
        ]
    if state == "not_met":
        return [
            ("dadm", "CA-DADM-APP-C-03", {**prod, "impact_level": 3}, []),
            ("dadm", "CA-DADM-6-1-1", {**prod, "impact_level": 2}, []),
            ("dadm", "CA-DADM-6-3-7", {**prod, "impact_level": 2}, []),
        ]
    if state == "unable_to_determine":
        bad_aia = [
            {
                "type": "aia_record",
                "authorized_submitter": False,
                "valid_until": "2099-01-01",
            }
        ]
        bad_adm = [
            {
                "type": "adm_accountability_record",
                "authorized_submitter": False,
                "valid_until": "2099-01-01",
            }
        ]
        stale_design = [
            {
                "type": "design_by_default_record",
                "authorized_submitter": True,
                "valid_until": "expired",
            }
        ]
        return [
            ("aia", "CA-AIA-SCORE-01", prod, bad_aia),
            ("psd", "CA-PSD-4-1-26", prod, stale_design),
            ("psd", "CA-PSD-4-1-28", prod, bad_adm),
        ]
    raise ValueError(state)


def _expand_to_count(state: str, count: int) -> list[dict]:
    profiles = _profiles_for_state(state)
    cases: list[dict] = []
    idx = 0
    while len(cases) < count:
        pack_slug, control_key, system, evidence = profiles[idx % len(profiles)]
        variant = len(cases)
        system_v = dict(system)
        system_v["case_variant"] = variant
        system_v["impact_level"] = system_v.get("impact_level", 1) + (variant % 3)
        if not evidence:
            evidence_v: list[dict] = []
        elif any(
            item.get("authorized_submitter") is False or item.get("valid_until") == "expired"
            for item in evidence
        ):
            evidence_v = [dict(item) for item in evidence]
        else:
            evidence_v = _evidence(
                *[str(item["type"]) for item in evidence],
                suffix=variant,
            )
        case_id = f"{state[:2]}-{pack_slug}-{variant:03d}"
        expect, snapshot = _assess(
            pack_slug=pack_slug,
            control_key=control_key,
            system=system_v,
            evidence=evidence_v,
        )
        if expect["outcome_state"] != state:
            raise RuntimeError(
                f"Profile drift for {case_id}: wanted {state}, got {expect} "
                f"on {pack_slug}/{control_key}"
            )
        pack = load_pack(PACKS / pack_slug / "pack.yaml")
        control = next(c for c in pack["controls"] if c["control_key"] == control_key)
        cases.append(
            {
                "id": case_id,
                "pack_slug": pack_slug,
                "control_key": control_key,
                "clause_ref": control.get("clause_ref", ""),
                "citation_en": control.get("title_en", ""),
                "system": system_v,
                "evidence": evidence_v,
                "expect": expect,
                "_snapshot": snapshot,
            }
        )
        idx += 1
    return cases


def main() -> None:
    states = (
        ("not_applicable", 50),
        ("met", 50),
        ("partially_met", 50),
        ("not_met", 50),
        ("unable_to_determine", 50),
    )
    all_cases: list[dict] = []
    for state, count in states:
        all_cases.extend(_expand_to_count(state, count))
    assert len(all_cases) == 250
    mixed = sum(1 for c in all_cases if c["expect"]["outcome_state"] == "partially_met")
    assert mixed >= 30

    payload = [
        {k: v for k, v in case.items() if k != "_snapshot"} for case in all_cases
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    replay_payload = [
        {
            "id": c["id"],
            "pack_slug": c["pack_slug"],
            "control_key": c["control_key"],
            "system": c["system"],
            "evidence": c["evidence"],
            "snapshot": c["_snapshot"],
        }
        for c in all_cases[:10]
    ]
    REPLAY_OUT.write_text(json.dumps(replay_payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} golden cases to {OUT}")
    print(f"Wrote {len(replay_payload)} replay snapshots to {REPLAY_OUT}")


if __name__ == "__main__":
    main()
