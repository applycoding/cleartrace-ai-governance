from __future__ import annotations

from pathlib import Path

from tools import freeze_fixtures as ff

ROOT = Path(__file__).resolve().parents[2]
LICENSES = ROOT / "tests" / "fixtures" / "LICENSES.md"


def test_freeze_fixtures_preserves_manual_licence_rows(tmp_path: Path, monkeypatch) -> None:
    manual_row = (
        "| `../../services/risk/fixtures/uci/adult.data` | https://archive.ics.uci.edu/ | "
        "CC BY 4.0 | UCI Adult manual row | `abc123` |"
    )
    existing = "\n".join(
        [
            "# Fixtures licence register (step 4)",
            "",
            "| File | Source | Licence | Attribution | SHA-256 |",
            "| --- | --- | --- | --- | --- |",
            manual_row,
            "",
            "Run `uv run python tools/freeze_fixtures.py` before G0 to refresh managed rows.",
            "",
        ]
    )
    licences = tmp_path / "LICENSES.md"
    licences.write_text(existing, encoding="utf-8")
    monkeypatch.setattr(ff, "LICENSES_PATH", licences)
    monkeypatch.setattr(ff, "FIXTURES", tmp_path)
    monkeypatch.setattr(ff, "MANIFEST_PATH", tmp_path / "manifest.json")
    monkeypatch.setattr(ff, "CHECKSUMS_PATH", tmp_path / "checksums.sha256")

    synthetic = ff.SPECS[-1]
    target = tmp_path / synthetic.rel_path
    ff._write_synthetic(target)

    new_rows = {
        synthetic.rel_path: (
            f"| `{synthetic.rel_path}` | generated | {synthetic.licence} | "
            f"{synthetic.attribution} | `deadbeef` |"
        )
    }
    merged = ff._merge_licence_markdown(existing, {}, new_rows)
    licences.write_text(merged, encoding="utf-8")
    text = licences.read_text(encoding="utf-8")
    assert manual_row in text
    assert synthetic.rel_path in text
