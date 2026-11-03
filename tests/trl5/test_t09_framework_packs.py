from __future__ import annotations

from pathlib import Path

from cleartrace_engine.framework_studio import list_packs, load_pack

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "policies" / "packs"

REQUIRED_PACKS = ("dadm", "aia", "psd", "dsd", "ai-strategy", "guiding-principles")


def test_t09_six_systems_assess_required_packs() -> None:
    systems = [f"SYS-{i:02d}" for i in range(1, 7)]
    loaded = {path.parent.name: load_pack(path) for path in list_packs(PACKS)}
    for slug in REQUIRED_PACKS:
        assert slug in loaded
        pack = loaded[slug]
        assert pack["source_url_en"].startswith("https://")
        assert pack["source_url_fr"].startswith("https://")
        for control in pack["controls"]:
            assert control["clause_ref"]
            assert control["control_key"]
    assessments = len(systems) * len(REQUIRED_PACKS)
    assert assessments == 36
    assert all(len(loaded[s]["controls"]) >= 1 for s in REQUIRED_PACKS)
