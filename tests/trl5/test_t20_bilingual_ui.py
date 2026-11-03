"""TRL 5 — T-20: bilingual UI, locale parity and core journey checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"


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


def test_t20_language_review_record_exists() -> None:
    review = ROOT / "tests" / "trl5" / "t20_language_review.json"
    data = json.loads(review.read_text(encoding="utf-8"))
    assert data["reviewer"]
    assert data["languages"] == ["en-CA", "fr-CA"]
    assert data["screens_reviewed"] >= 8
