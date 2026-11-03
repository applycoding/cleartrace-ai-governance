from __future__ import annotations

from pathlib import Path

from cleartrace_engine.framework_studio import list_packs, load_pack, pack_to_oscal_catalog

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "policies" / "packs"


def test_all_starter_packs_load_and_require_second_reader() -> None:
    slugs = {p.parent.name for p in list_packs(PACKS)}
    expected = {
        "dadm",
        "aia",
        "psd",
        "dsd",
        "ai-strategy",
        "guiding-principles",
        "nist-ai-rmf",
        "iso42001-ids",
    }
    assert expected.issubset(slugs)
    for path in list_packs(PACKS):
        pack = load_pack(path)
        assert pack["needs_second_reader_recheck"] is True
        oscal = pack_to_oscal_catalog(pack)
        assert "catalog" in oscal
        assert oscal["catalog"]["controls"]
