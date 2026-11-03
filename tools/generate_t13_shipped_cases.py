#!/usr/bin/env python3
"""Generate shipped-policy golden cases and replay snapshots for T-13."""

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
MIXED_OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_shipped_mixed_cases.json"
REPLAY_OUT = ROOT / "tests" / "trl5" / "fixtures" / "t13_rule_replay_snapshots.json"


def _case(
    case_id: str,
    *,
    pack_slug: str,
    control_key: str,
    system: dict,
    evidence: list,
) -> dict:
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
    return {
        "id": case_id,
        "pack_slug": pack_slug,
        "control_key": control_key,
        "system": system,
        "evidence": evidence,
        "expect": {
            "outcome_state": output.outcome_state,
            "reason_code": output.reason_code,
        },
        "snapshot": asdict(output),
    }


def main() -> None:
    cases: list[dict] = []
    profiles = [
        (
            "dadm",
            "CA-DADM-APP-C-03",
            {"planned_production_use": True, "impact_level": 3},
            [],
        ),
        (
            "dadm",
            "CA-DADM-APP-C-03",
            {"planned_production_use": True, "impact_level": 1},
            [
                {
                    "type": "peer_review_report",
                    "authorized_submitter": True,
                    "valid_until": "2099-01-01",
                }
            ],
        ),
        (
            "dadm",
            "CA-DADM-6-1-1",
            {"planned_production_use": True, "impact_level": 2},
            [],
        ),
        (
            "dadm",
            "CA-DADM-6-1-1",
            {"planned_production_use": True, "impact_level": 2},
            [
                {"type": "aia_record", "authorized_submitter": True, "valid_until": "2099-01-01"}
            ],
        ),
        (
            "aia",
            "CA-AIA-SCORE-01",
            {"planned_production_use": True},
            [],
        ),
        (
            "aia",
            "CA-AIA-SCORE-01",
            {"planned_production_use": True},
            [
                {
                    "type": "aia_record",
                    "authorized_submitter": True,
                    "valid_until": "2099-01-01",
                }
            ],
        ),
        (
            "psd",
            "CA-PSD-4-1-28",
            {"planned_production_use": True},
            [],
        ),
        (
            "psd",
            "CA-PSD-4-1-28",
            {"planned_production_use": True},
            [
                {
                    "type": "design_by_default_record",
                    "authorized_submitter": True,
                    "valid_until": "2099-01-01",
                }
            ],
        ),
        (
            "guiding-principles",
            "CA-AI-PRIN-01",
            {"planned_production_use": True},
            [],
        ),
        (
            "guiding-principles",
            "CA-AI-PRIN-01",
            {"planned_production_use": True},
            [
                {
                    "type": "principle_alignment_record",
                    "authorized_submitter": True,
                    "valid_until": "2099-01-01",
                }
            ],
        ),
    ]
    idx = 0
    while len(cases) < 30:
        for pack_slug, control_key, system, evidence in profiles:
            case_id = f"shipped-mixed-{idx:02d}"
            cases.append(
                _case(
                    case_id,
                    pack_slug=pack_slug,
                    control_key=control_key,
                    system=dict(system),
                    evidence=list(evidence),
                )
            )
            idx += 1
            if len(cases) >= 30:
                break

    MIXED_OUT.parent.mkdir(parents=True, exist_ok=True)
    mixed_payload = [
        {
            "id": c["id"],
            "pack_slug": c["pack_slug"],
            "control_key": c["control_key"],
            "system": c["system"],
            "evidence": c["evidence"],
            "expect": c["expect"],
        }
        for c in cases
    ]
    MIXED_OUT.write_text(json.dumps(mixed_payload, indent=2), encoding="utf-8")
    replay_payload = [
        {
            "id": c["id"],
            "pack_slug": c["pack_slug"],
            "control_key": c["control_key"],
            "system": c["system"],
            "evidence": c["evidence"],
            "snapshot": c["snapshot"],
        }
        for c in cases[:10]
    ]
    REPLAY_OUT.write_text(json.dumps(replay_payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} mixed cases to {MIXED_OUT}")
    print(f"Wrote {len(replay_payload)} replay snapshots to {REPLAY_OUT}")


if __name__ == "__main__":
    main()
