"""TRL 5 — T-20: bilingual UI, locale parity and core journey checks."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
REVIEW_SHEET = ROOT / "docs" / "trl5" / "t20_language_review_sheet.csv"


def test_t20_locale_files_have_zero_missing_keys() -> None:
    result = subprocess.run(
        ["node", "scripts/check-i18n.mjs"],
        cwd=WEB,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["missing_keys"] == 0
    assert payload["hard_coded_strings"] == 0


def test_t20_human_language_review_pending() -> None:
    assert REVIEW_SHEET.is_file()
    with REVIEW_SHEET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) >= 8
    for row in rows:
        assert row["verdict"].strip() == ""
        assert row["reviewer name"].strip() == ""
        assert row["date"].strip() == ""
