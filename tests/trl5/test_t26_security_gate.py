from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "docs" / "security" / "ASVS_L2_MAPPING.md"
IDS = ROOT / "docs" / "security" / "asvs_4.0.3_l2_ids.txt"
TRIAGE = ROOT / "docs" / "security" / "FINDINGS_TRIAGE.md"
CORE_API = ROOT / "services" / "core-api" / "src" / "cleartrace_core_api"
ROW = re.compile(r"^\|\s*(V\d+\.\d+\.\d+)\s*\|\s*(Pass|Fail|N/A)\s*\|\s*(.+?)\s*\|\s*$")
TOTALS = re.compile(r"Totals: (\d+) Pass, (\d+) Fail, (\d+) N/A \((\d+) requirements\)")
PATHLIKE = re.compile(r"`([^`\s]+)`")
SHORTHAND = ("routers/", "auth/", "middleware/", "errors/")


def _rows() -> list[tuple[str, str, str]]:
    rows = []
    for line in MAPPING.read_text(encoding="utf-8").splitlines():
        if line.startswith("| V"):
            match = ROW.match(line)
            assert match, f"malformed mapping row: {line}"
            req, status, evidence = match.groups()
            rows.append((req, status, evidence))
    return rows


FILE_SUFFIX = re.compile(r"\.(py|md|ya?ml|json|txt|lock|cedar|ts|tsx|toml|sh|tpl)$")


def _cited_paths(evidence: str) -> list[str]:
    return [p for p in PATHLIKE.findall(evidence) if "/" in p or FILE_SUFFIX.search(p)]


def _exists(cited: str) -> bool:
    if (ROOT / cited).exists():
        return True
    return cited.startswith(SHORTHAND) and (CORE_API / cited).exists()


@pytest.mark.trl5
def test_t26_mapping_lists_exactly_the_asvs_l2_requirements() -> None:
    expected = [
        line.strip()
        for line in IDS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(expected) == 259, "ASVS 4.0.3 has 259 Level 2 requirements"
    assert [req for req, _s, _e in _rows()] == expected


@pytest.mark.trl5
def test_t26_every_pass_cites_evidence_that_exists() -> None:
    for req, status, evidence in _rows():
        assert evidence.strip(), f"{req}: no evidence or reason"
        assert "TODO" not in evidence and "TBD" not in evidence, req
        if status != "Pass":
            continue
        cited = _cited_paths(evidence)
        assert cited, f"{req}: a Pass must cite a file or test in this repository"
        for path in cited:
            assert _exists(path), f"{req}: cited path does not exist: {path}"


@pytest.mark.trl5
def test_t26_mapping_totals_match_the_table() -> None:
    counts = Counter(status for _r, status, _e in _rows())
    match = TOTALS.search(MAPPING.read_text(encoding="utf-8"))
    assert match, "mapping must state its Pass/Fail/N/A totals"
    stated = tuple(int(x) for x in match.groups())
    assert stated == (counts["Pass"], counts["Fail"], counts["N/A"], 259)


@pytest.mark.trl5
def test_t26_triage_entries_are_justified() -> None:
    allowed = {"false positive", "open", "fixed"}
    entries = 0
    for line in TRIAGE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != 5 or cells[0] in {"Scanner", "---"}:
            continue
        if set(cells[0]) <= {"-", " "}:
            continue
        entries += 1
        _tool, rule, severity, disposition, justification = cells
        assert rule, f"triage row without a rule: {line}"
        assert severity.lower() in {"critical", "high", "medium", "low", "info"}, line
        assert disposition.lower() in allowed, f"unknown disposition: {line}"
        assert len(justification) >= 40, f"justification too short: {line}"
    assert entries > 0, "FINDINGS_TRIAGE.md must record the findings of the evidence run"
