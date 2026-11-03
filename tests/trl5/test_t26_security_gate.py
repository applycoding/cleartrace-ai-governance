from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "docs" / "security" / "ASVS_L2_MAPPING.md"
TRIAGE = ROOT / "docs" / "security" / "FINDINGS_TRIAGE.md"
ROW = re.compile(
    r"^\|\s*(V\d+\.\d+\.\d+)\s*\|\s*(Pass|Fail|N/A)\s*\|\s*(.+?)\s*\|\s*$",
    re.IGNORECASE,
)


@pytest.mark.trl5
def test_t26_asvs_l2_mapping_has_evidence_for_every_row() -> None:
    assert MAPPING.is_file(), "docs/security/ASVS_L2_MAPPING.md required for T-26"
    rows = [line for line in MAPPING.read_text(encoding="utf-8").splitlines() if line.startswith("| V")]
    assert len(rows) >= 50, "expected ASVS 4.0.3 Level 2 mapping rows"
    for line in rows:
        match = ROW.match(line)
        assert match, f"malformed mapping row: {line}"
        _req, status, evidence = match.groups()
        assert evidence.strip(), f"missing evidence pointer for {line}"
        if status.lower() == "pass":
            assert "TODO" not in evidence and "TBD" not in evidence


@pytest.mark.trl5
def test_t26_findings_triage_doc_exists() -> None:
    assert TRIAGE.is_file()
