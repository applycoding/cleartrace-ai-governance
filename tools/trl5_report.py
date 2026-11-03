#!/usr/bin/env python3
"""Build TRL 5 test report (blueprint sections 18–19) from pytest JUnit XML."""

from __future__ import annotations

import argparse
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "trl5" / "TRL5_TEST_REPORT.md"

# fmt: off
CRITERIA: dict[str, tuple[str, str, str]] = {
    "T-01": ("E", "10/10 substantive detected; 0/10 formatting-only activated", "tests/trl5/test_t01_policy_change.py"),
    "T-02": ("E", "90/90 field slots filled; simulator setup ≤ 15 min", "tests/trl5/test_t02_connectors_register.py"),
    "T-03": ("R", "100% schema-valid exports; 50/50 outcome states preserved", "tests/trl5/test_t03_oscal_cyclonedx.py"),
    "T-04": ("R", "0 lost updates; conflicts quarantined", "tests/trl5/test_t04_source_precedence.py"),
    "T-05": ("R", "Restore completes; checksums match 100%", "tests/integration/test_t05_backup_restore.py"),
    "T-06": ("E", "600/600 allowed; 0/600 forbidden; denials audited", "tests/trl5/test_t06_audit_slice.py"),
    "T-07": ("E", "0 held records deleted; due records removed with certificate", "tests/integration/test_t07_deletion.py"),
    "T-08": ("E", "40/40 non-conformities; 140 explanation pairs ≥ 95% (human review)", "tests/trl5/test_t08_control_manifest.py"),
    "T-09": ("E", "Six systems assessed against five packs", "tests/trl5/test_t09_framework_packs.py"),
    "T-10": ("E", "Group assignments and retire/replace reassessment", "tests/trl5/test_t10_assignments.py"),
    "T-11": ("R", "Certainty index calibration thresholds or reported uncalibrated", "tests/trl5/test_t11_certainty_index.py"),
    "T-12": ("E", "500 artefacts with provenance; unauthorized blocked", "tests/trl5/test_t12_evidence_store.py"),
    "T-13": ("E", "250/250 golden five-state cases", "tests/trl5/test_t13_five_states.py"),
    "T-14": ("E", "200 reviewer actions; 0 self-reviews; stale → 409", "tests/trl5/test_t14_reviewer_workflow.py"),
    "T-15": ("E", "30/30 binding vs advisory breach behaviour", "tests/trl5/test_t15_risk_breaches.py"),
    "T-16": ("R", "≥ 48/50 defective windows flagged per defect type", "tests/trl5/test_t16_data_quality_windows.py"),
    "T-17": ("R", "12/12 custom metrics; 0 sandbox escapes", "tests/trl5/test_t17_custom_metrics.py"),
    "T-18": ("R", "≥ 48/50 seeded output failures detected", "tests/trl5/test_t18_output_monitoring.py"),
    "T-19": ("R", "Same signed images on 2 environments; smoke passes", "tests/trl5/test_t19_install_smoke.py"),
    "T-20": ("R", "EN/FR UI journeys; human language review sheet", "tests/trl5/test_t20_bilingual_ui.py"),
    "T-21": ("R", "Three tenants isolated", "not_implemented"),
    "T-22": ("R", "50/50 alerts delivered; no duplicate tickets", "tests/trl5/test_t22_alert_delivery.py"),
    "T-23": ("E", "100% tamper detected after checkpoint", "tests/trl5/test_t23_audit_tamper.py"),
    "T-24": ("D/R", "LLM irrelevant quote rejection (if LLM pilot)", "not_implemented"),
    "T-25": ("D", "Outbox/NATS crash windows at scale", "not_implemented"),
    "T-26": ("E", "0 critical/high SAST/DAST; ASVS L2 mapping", "not_implemented"),
    "T-27": ("D", "Large-scale bitemporal performance", "not_implemented"),
    "T-28": ("E", "SBOM complete; licence gate clean", "tests/trl5/test_t28_sbom.py"),
    "T-29": ("R", "0 cross-tenant leaks in 1,000 transactions", "not_implemented"),
    "T-30": ("D", "Replay past assessment from stored inputs", "not_implemented"),
}
# fmt: on

NOT_COVERED_NOTES: dict[str, str] = {
    "T-05": "Same-VM restore target not fully exercised in CI; integration test records checksums only.",
    "T-08": "Automated suite seeds manifest; dual human reviewer sheet stays blank pending G0 sign-off.",
    "T-19": "Second environment install and cosign image signing not run in CI.",
    "T-20": "Automated i18n checks only; human language review columns intentionally blank.",
    "T-21": "Multi-tenant concurrent policy test not implemented.",
    "T-24": "Deferred unless LLM evidence pilot is enabled.",
    "T-25": "Deferred to contract period; unit coverage on outbox idempotency only.",
    "T-26": "Security suite mapping incomplete in this repository snapshot.",
    "T-27": "Deferred performance scale test.",
    "T-29": "Reduced-scope leak test not implemented at 1,000 tx.",
    "T-30": "Deterministic replay deferred for LLM branches.",
}


@dataclass(frozen=True)
class JunitCase:
    classname: str
    name: str
    time: float
    failed: bool
    skipped: bool


def _parse_junit(path: Path) -> list[JunitCase]:
    if not path.is_file():
        return []
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    cases: list[JunitCase] = []
    for suite in root.iter("testsuite"):
        for case in suite.iter("testcase"):
            failed = case.find("failure") is not None or case.find("error") is not None
            skipped = case.find("skipped") is not None
            cases.append(
                JunitCase(
                    classname=str(case.get("classname", "")),
                    name=str(case.get("name", "")),
                    time=float(case.get("time", "0") or 0),
                    failed=failed,
                    skipped=skipped,
                )
            )
    return cases


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _match_test(path_hint: str, cases: list[JunitCase]) -> JunitCase | None:
    if path_hint == "not_implemented":
        return None
    stem = Path(path_hint).stem
    for case in cases:
        if stem in case.classname or stem in case.name:
            return case
    return None


def _status_for(test_id: str, case: JunitCase | None) -> str:
    hint = CRITERIA[test_id][2]
    if hint == "not_implemented":
        return "not covered"
    if case is None:
        return "pending"
    if case.skipped:
        return "pending"
    if case.failed:
        return "fail"
    return "pass"


def _measurement(case: JunitCase | None) -> str:
    if case is None:
        return "No JUnit result captured for this run."
    if case.skipped:
        return "Skipped in pytest output."
    if case.failed:
        return f"Failed: {case.classname}::{case.name}"
    return f"Passed in {case.time:.2f}s ({case.classname}::{case.name})"


def _render_table(cases: list[JunitCase], *, lang: str) -> str:
    headers_en = (
        "| Test | Tier | Pass criterion (summary) | Measured result | Status | "
        "Environment | Commit | Tester | Job title | Witness | Date |"
    )
    headers_fr = (
        "| Test | Niveau | Critère de réussite (résumé) | Résultat mesuré | Statut | "
        "Environnement | Commit | Testeur | Titre de poste | Témoin | Date |"
    )
    header = headers_fr if lang == "fr" else headers_en
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [header, sep]
    commit = _git_sha()
    env = "GitHub Actions CI (simulated GoC stack)" if lang == "en" else "CI GitHub Actions (pile GoC simulée)"
    for test_id in sorted(CRITERIA.keys()):
        tier, criterion, hint = CRITERIA[test_id]
        case = _match_test(hint, cases)
        status = _status_for(test_id, case)
        note = NOT_COVERED_NOTES.get(test_id, "")
        measurement = _measurement(case)
        if note and status in {"not covered", "pending", "pass"}:
            measurement = f"{measurement} Note: {note}"
        lines.append(
            f"| {test_id} | {tier} | {criterion} | {measurement} | {status} | "
            f"{env} | `{commit}` | | | | |"
        )
    return "\n".join(lines)


def build_report(*, junit_paths: list[Path]) -> str:
    cases: list[JunitCase] = []
    for path in junit_paths:
        cases.extend(_parse_junit(path))
    generated = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    en = [
        "# TRL 5 test report (English)",
        "",
        f"Generated: {generated}. Commit `{_git_sha()}`.",
        "",
        "Tester name, job title, witness and date columns are left blank for manual completion.",
        "",
        _render_table(cases, lang="en"),
        "",
        "## Not yet fully met (honest status)",
        "",
    ]
    for test_id, note in sorted(NOT_COVERED_NOTES.items()):
        en.append(f"- **{test_id}**: {note}")
    en.extend(
        [
            "",
            "---",
            "",
            "# Rapport de tests TRL 5 (français)",
            "",
            f"Généré : {generated}. Commit `{_git_sha()}`.",
            "",
            "Les colonnes testeur, titre de poste, témoin et date restent vides pour saisie manuelle.",
            "",
            _render_table(cases, lang="fr"),
            "",
        ]
    )
    return "\n".join(en) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate TRL5_TEST_REPORT.md from JUnit XML.")
    parser.add_argument("--junit-unit", type=Path, default=None)
    parser.add_argument("--junit-integration", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    paths = [p for p in (args.junit_unit, args.junit_integration) if p]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(junit_paths=paths), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
