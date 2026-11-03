#!/usr/bin/env python3
"""Build TRL 5 test report (blueprint sections 18–19) from pytest JUnit XML."""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
    "T-21": ("R", "Three tenants isolated", "tests/trl5/test_t21_multi_tenant.py"),
    "T-22": ("R", "50/50 alerts delivered; no duplicate tickets", "tests/trl5/test_t22_alert_delivery.py"),
    "T-23": ("E", "100% tamper detected after checkpoint", "tests/trl5/test_t23_audit_tamper.py"),
    "T-24": ("D/R", "LLM irrelevant quote rejection (if LLM pilot)", "not_implemented"),
    "T-25": ("D", "Outbox/NATS crash windows at scale", "not_implemented"),
    "T-26": ("E", "0 critical/high SAST/DAST; ASVS L2 mapping", "tests/trl5/test_t26_security_gate.py"),
    "T-27": ("D", "Large-scale bitemporal performance", "not_implemented"),
    "T-28": ("E", "SBOM complete; licence gate clean", "tests/trl5/test_t28_sbom.py"),
    "T-29": ("R", "0 cross-tenant leaks in 1,000 transactions", "tests/integration/test_t29_pooled_leak.py"),
    "T-30": ("D", "Replay past assessment from stored inputs", "not_implemented"),
}
# fmt: on

# Tests whose suite exists and can pass in CI but does not yet exercise the full
# section 18 pass criterion. A green run for these is reported as "partial".
PARTIAL_NOTES: dict[str, str] = {
    "T-03": "Exports and validates 2 dossiers but checks 10 findings, not 50/50 outcome states.",
    "T-05": "Restore target is a second Postgres container on the same CI runner, not a clean node.",
    "T-06": "Audits 60 denials and 60 privileged reads; the 600 allowed + 600 forbidden matrix across 3 tenants and 6 roles is not run.",
    "T-08": "Automated 40/40 non-conformities pass; the 140 explanation pairs await two human reviewers (xfail by design).",
    "T-18": "Each dimension repeats one fixed synthetic input 50 times; no public set and no varied seeded degradations.",
    "T-19": "One CI environment only; images unsigned (cosign pending); no second install.",
    "T-20": "Automated i18n checks only; human language review sheet intentionally blank.",
    "T-23": "Edit, delete, reorder and truncate detected; the exposure window is not asserted.",
    "T-28": "Repository SBOM and licence gate only; shipped container images are not inventoried.",
}

NOT_COVERED_NOTES: dict[str, str] = {
    "T-24": "Runs only if the LLM evidence pilot runs; not implemented.",
    "T-25": "Deferred to the contract period (section 18); mechanism unit-tested.",
    "T-27": "Deferred to the contract period (section 18).",
    "T-30": "Deferred for LLM parts (section 18); rule-only replay is covered by T-13 shipped replay cases.",
}

MULTI_MODULE: dict[str, list[str]] = {
    "T-13": [
        "tests/trl5/test_t13_five_states.py",
        "tests/trl5/test_t13_shipped_policies.py",
    ],
}


@dataclass(frozen=True)
class JunitCase:
    classname: str
    name: str
    time: float
    failed: bool
    skipped: bool


@dataclass(frozen=True)
class Outcome:
    passed: int
    failed: int
    skipped: int
    seconds: float

    @property
    def ran(self) -> int:
        return self.passed + self.failed


def _parse_junit(path: Path) -> list[JunitCase]:
    if not path.is_file():
        raise FileNotFoundError(f"JUnit file not found: {path}")
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    cases: list[JunitCase] = []
    for case in root.iter("testcase"):
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        cases.append(
            JunitCase(
                classname=str(case.get("classname", "")),
                name=str(case.get("name", "")),
                time=float(case.get("time", "0") or 0),
                failed=failed,
                skipped=skipped and not failed,
            )
        )
    return cases


def _module_of(case: JunitCase) -> str:
    return case.classname.split(".")[-1] if case.classname else ""


def _outcome_for(path_hint: str, cases: list[JunitCase]) -> Outcome | None:
    if path_hint == "not_implemented":
        return None
    stem = Path(path_hint).stem
    matched = [c for c in cases if _module_of(c) == stem or c.classname.endswith(f".{stem}")]
    if not matched:
        return None
    return Outcome(
        passed=sum(1 for c in matched if not c.failed and not c.skipped),
        failed=sum(1 for c in matched if c.failed),
        skipped=sum(1 for c in matched if c.skipped),
        seconds=sum(c.time for c in matched),
    )


def _outcome_for_test(test_id: str, cases: list[JunitCase]) -> Outcome | None:
    hints = MULTI_MODULE.get(test_id)
    if hints is None:
        _tier, _criterion, hint = CRITERIA[test_id]
        return _outcome_for(hint, cases)
    combined: Outcome | None = None
    for hint in hints:
        part = _outcome_for(hint, cases)
        if part is None:
            return None
        if combined is None:
            combined = part
        else:
            combined = Outcome(
                passed=combined.passed + part.passed,
                failed=combined.failed + part.failed,
                skipped=combined.skipped + part.skipped,
                seconds=combined.seconds + part.seconds,
            )
    return combined


def status_for(test_id: str, outcome: Outcome | None) -> str:
    tier, _criterion, hint = CRITERIA[test_id]
    if hint == "not_implemented":
        return "deferred" if tier == "D" else "not covered"
    if outcome is None or outcome.ran == 0:
        return "not run"
    if outcome.failed:
        return "fail"
    if outcome.skipped or test_id in PARTIAL_NOTES:
        return "partial"
    return "pass"


def _measurement(test_id: str, outcome: Outcome | None) -> str:
    note = PARTIAL_NOTES.get(test_id) or NOT_COVERED_NOTES.get(test_id, "")
    if outcome is None:
        text = "No test case for this ID in the CI JUnit results."
    else:
        text = (
            f"JUnit case runs: {outcome.passed} passed, {outcome.failed} failed, "
            f"{outcome.skipped} skipped/xfailed ({outcome.seconds:.2f}s)."
        )
    return f"{text} {note}".strip()


def _render_table(cases: list[JunitCase], *, lang: str, commit: str, run_label: str) -> str:
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
    env = f"GitHub Actions CI, {run_label}" if lang == "en" else f"CI GitHub Actions, {run_label}"
    for test_id in sorted(CRITERIA.keys()):
        tier, criterion, hint = CRITERIA[test_id]
        outcome = _outcome_for_test(test_id, cases)
        status = status_for(test_id, outcome)
        if lang == "fr":
            status = STATUS_FR[status]
        lines.append(
            f"| {test_id} | {tier} | {criterion} | {_measurement(test_id, outcome)} | {status} | "
            f"{env} | `{commit[:12]}` | | | | |"
        )
    return "\n".join(lines)


STATUS_FR = {
    "pass": "réussi",
    "partial": "partiel",
    "fail": "échec",
    "not run": "non exécuté",
    "not covered": "non couvert",
    "deferred": "reporté",
}


def build_report(*, junit_paths: list[Path], run_id: str, run_url: str, commit: str) -> str:
    cases: list[JunitCase] = []
    for path in junit_paths:
        cases.extend(_parse_junit(path))
    if not cases:
        raise ValueError("no JUnit test cases found; refusing to write an empty report")
    run_label = f"run {run_id}" if run_id else "local run (no CI run id)"
    counts: dict[str, int] = {}
    for test_id in CRITERIA:
        status = status_for(test_id, _outcome_for_test(test_id, cases))
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    source = f"[{run_label}]({run_url})" if run_url else run_label
    en = [
        "# TRL 5 test report (English)",
        "",
        f"Source: JUnit XML from CI {source}, commit `{commit}`.",
        "",
        "A test ID is **pass** only when every JUnit case from its test module ran and passed and "
        "the review of that suite against section 18 found no coverage gap. **partial** means the "
        "cases ran and passed (or were xfailed by design) but the suite does not yet cover the "
        "whole criterion. **not covered** and **deferred** have no test. Counts are case runs "
        "summed over the unit and integration CI stages; modules without the integration marker "
        "run in both stages, so their cases are counted twice.",
        "",
        f"Summary: {summary}.",
        "",
        "Tester name, job title, witness and date columns are left blank for manual completion.",
        "",
        _render_table(cases, lang="en", commit=commit, run_label=run_label),
        "",
        "---",
        "",
        "# Rapport de tests TRL 5 (français)",
        "",
        f"Source : JUnit XML de la CI {source}, commit `{commit}`.",
        "",
        "Les notes de mesure restent en anglais (sortie brute de la CI). Les colonnes testeur, titre "
        "de poste, témoin et date restent vides pour saisie manuelle.",
        "",
        _render_table(cases, lang="fr", commit=commit, run_label=run_label),
        "",
    ]
    return "\n".join(en) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate TRL5_TEST_REPORT.md from JUnit XML.")
    parser.add_argument("--junit-unit", type=Path, default=None)
    parser.add_argument("--junit-integration", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "unknown"))
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()
    run_url = args.run_url
    if not run_url and args.run_id and os.environ.get("GITHUB_REPOSITORY"):
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        run_url = f"{server}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{args.run_id}"
    paths = [p for p in (args.junit_unit, args.junit_integration) if p]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(junit_paths=paths, run_id=args.run_id, run_url=run_url, commit=args.commit)
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
