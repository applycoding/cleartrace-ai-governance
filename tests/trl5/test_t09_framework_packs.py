from __future__ import annotations

import json
from pathlib import Path

from cleartrace_engine.framework_studio import list_packs, load_pack
from cleartrace_engine.pipeline import assess_pack_control, finding_metadata

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "policies" / "packs"
SYSTEMS = ROOT / "tests" / "fixtures" / "t09_systems.json"

REQUIRED_PACKS = ("dadm", "aia", "psd", "ai-strategy", "guiding-principles")


def test_t09_six_systems_five_packs_end_to_end() -> None:
    systems = json.loads(SYSTEMS.read_text(encoding="utf-8"))["systems"]
    assert len(systems) == 6
    findings: list[dict[str, str]] = []
    for system in systems:
        for slug in REQUIRED_PACKS:
            pack = load_pack(PACKS / slug / "pack.yaml")
            for control in pack["controls"]:
                output, ctx = assess_pack_control(
                    pack=pack,
                    control=control,
                    system=system,
                    evidence=system.get("evidence", []),
                    pack_slug=slug,
                    cel_context=system,
                )
                meta = finding_metadata(pack, control, ctx)
                findings.append(
                    {
                        "system_key": system["system_key"],
                        "pack": slug,
                        "outcome_state": output.outcome_state,
                        **meta,
                    }
                )
                assert meta["clause_ref"]
                assert meta["control_version"]
                assert meta["source_url_en"].startswith("https://")
                assert meta["source_url_fr"].startswith("https://")
                assert meta["control_key"] == control["control_key"]
    assert len(findings) == 6 * sum(
        len(load_pack(PACKS / slug / "pack.yaml")["controls"]) for slug in REQUIRED_PACKS
    )
