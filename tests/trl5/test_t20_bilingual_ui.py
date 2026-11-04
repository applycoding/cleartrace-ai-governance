"""TRL 5 — T-20: bilingual UI, locale parity and core journey checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from tools.review_sheets import (
    t20_acceptable_verdicts,
    t20_fill_state,
    t20_load_rows,
    t20_pass_threshold,
)

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


def test_t20_language_review_sheet() -> None:
    assert REVIEW_SHEET.is_file(), "Run tools/generate_t20_review_sheet.py"
    rows = t20_load_rows()
    assert len(rows) >= 10
    categories = {row["category"] for row in rows}
    assert "screen" in categories
    assert "notification" in categories
    assert "report" in categories
    fill = t20_fill_state(rows)
    if fill.state == "blank":
        return
    if fill.state == "partial":
        pytest.fail(f"T-20 language sheet partly filled: {fill.detail}")
    acceptable = t20_acceptable_verdicts(rows)
    pass_bar = t20_pass_threshold(len(rows))
    assert acceptable >= pass_bar, (
        f"T-20 human gate: {acceptable}/{len(rows)} rows marked acceptable; need ≥{pass_bar} (95%)."
    )
