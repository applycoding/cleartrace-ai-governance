#!/usr/bin/env python3
"""Build TRL 5 test report (blueprint sections 18–19) from pytest JUnit XML."""

from __future__ import annotations

import argparse
import json
import os
import re
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
    "T-05": "Restore target is a second Postgres container on the same CI runner, not a clean node.",
    "T-08": "Automated 40/40 non-conformities pass; the 140 explanation pairs await two human reviewers (xfail by design).",
    "T-11": "Reported as an uncalibrated index: the held-out labels are derived from the corpus, not adjudicated by independent EN/FR reviewers (section 6), and the held-out cases are German-source only, so 'calibrated' is never claimed.",
    "T-13": "250 cases (50 per state) on the shipped packs pass, but they hold 67 behaviourally distinct inputs (not_applicable 13, met 13, partially_met 6, not_met 8, unable_to_determine 27); partially_met comes from one control (DADM 6.3.8 GBA+), and 59 cases only add unrelated evidence. Expected states are engine output checked against the selected state, not derived independently from the clause text. Rule-only replay of 10 snapshots passes.",
    "T-18": "50/50 detected and 0/50 false alarms per dimension, but the seeds are not 50 distinct failures: accuracy 8 and fairness 2 distinct failure inputs (real UCI German Credit class labels and UCI Adult sex column, predictions seeded), safety 2 (hand-written; no public harm or jailbreak set vendored); PII and EN/FR 50 each (hand-written synthetic).",
    "T-19": "One CI environment only; images unsigned (cosign pending); no second install.",
    "T-20": "Automated i18n checks only; human language review sheet intentionally blank.",
    "T-28": "Repository SBOM and licence gate cover source paths and container references only; Python dependency licences are not recorded, and shipped runtime dependencies include LGPL (psycopg, psycopg-pool, paramiko, svglib) and MPL-2.0 (orjson, certifi, tqdm) packages. Syft image SBOMs list OS packages of the third-party images, which carry GPL/LGPL/MPL-licensed packages; these are reported in the image-sbom artifact, not gated, and no approved exception file exists. The ClearTrace core-api image is not built or published, so it is not scanned.",
}

NOT_COVERED_NOTES: dict[str, str] = {
    "T-24": "Runs only if the LLM evidence pilot runs; not implemented.",
    "T-25": "Deferred to the contract period (section 18); mechanism unit-tested.",
    "T-27": "Deferred to the contract period (section 18).",
    "T-30": "Deferred for LLM parts (section 18); rule-only replay is covered by T-13 shipped replay cases.",
}

MULTI_MODULE: dict[str, list[str]] = {
    "T-06": [
        "tests/trl5/test_t06_audit_slice.py",
        "tests/trl5/test_t06_auth_matrix.py",
    ],
}


@dataclass(frozen=True)
class JunitCase:
    classname: str
    name: str
    time: float
    failed: bool
    skipped: bool
    properties: tuple[tuple[str, str], ...] = ()


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
        props = tuple(
            (str(p.get("name", "")), str(p.get("value", ""))) for p in case.iter("property")
        )
        cases.append(
            JunitCase(
                classname=str(case.get("classname", "")),
                name=str(case.get("name", "")),
                time=float(case.get("time", "0") or 0),
                failed=failed,
                skipped=skipped and not failed,
                properties=props,
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


def status_for(test_id: str, outcome: Outcome | None, t26: dict[str, object] | None = None) -> str:
    tier, _criterion, hint = CRITERIA[test_id]
    if hint == "not_implemented":
        return "deferred" if tier == "D" else "not covered"
    if outcome is None or outcome.ran == 0:
        return "not run"
    if outcome.failed:
        return "fail"
    # T-26 passes only on the security gate's own result over the real tool outputs.
    if test_id == "T-26" and (t26 is None or t26.get("gate_passed") is not True):
        return "fail"
    if outcome.skipped or test_id in PARTIAL_NOTES:
        return "partial"
    return "pass"


def _case_properties(test_id: str, cases: list[JunitCase]) -> dict[str, str]:
    _tier, _criterion, hint = CRITERIA[test_id]
    stem = Path(hint).stem
    props: dict[str, str] = {}
    for case in cases:
        if _module_of(case) == stem or case.classname.endswith(f".{stem}"):
            props.update(dict(case.properties))
    return props


def asvs_totals(mapping: Path) -> dict[str, int]:
    """Count Pass / Fail / N/A rows in the ASVS L2 mapping table."""
    totals = {"Pass": 0, "Fail": 0, "N/A": 0}
    if not mapping.is_file():
        return totals
    for line in mapping.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"V\d+\.\d+\.\d+", cells[0]) and cells[1] in totals:
            totals[cells[1]] += 1
    return totals


def _t26_text(t26: dict[str, object] | None) -> str:
    if t26 is None:
        return "No T-26 gate summary (artifacts/t26/t26_summary.json) was produced."
    by_tool = t26.get("by_tool")
    parts: list[str] = []
    if isinstance(by_tool, dict):
        for tool, counts in sorted(by_tool.items()):
            if isinstance(counts, dict):
                sevs = ", ".join(f"{sev} {n}" for sev, n in sorted(counts.items()))
                parts.append(f"{tool}: {sevs}")
    tools = "; ".join(parts)
    triaged = t26.get("triaged_false_positives")
    n_triaged = len(triaged) if isinstance(triaged, list) else 0
    asvs = asvs_totals(ROOT / "docs" / "security" / "ASVS_L2_MAPPING.md")
    return (
        f"Security gate {'passed' if t26.get('gate_passed') else 'FAILED'}: "
        f"{t26.get('findings_total', 0)} findings ({tools or 'none'}); "
        f"{t26.get('open_critical_high', 0)} open critical/high; "
        f"{n_triaged} triaged false positives; "
        f"{t26.get('schemathesis_cases', 0)} Schemathesis cases. "
        f"ASVS 4.0.3 L2 mapping: {asvs['Pass']} pass, {asvs['Fail']} fail, {asvs['N/A']} N/A."
    )


def _measurement(
    test_id: str,
    outcome: Outcome | None,
    cases: list[JunitCase] | None = None,
    t26: dict[str, object] | None = None,
) -> str:
    note = PARTIAL_NOTES.get(test_id) or NOT_COVERED_NOTES.get(test_id, "")
    if outcome is None:
        text = "No test case for this ID in the CI JUnit results."
    else:
        text = (
            f"JUnit case runs: {outcome.passed} passed, {outcome.failed} failed, "
            f"{outcome.skipped} skipped/xfailed ({outcome.seconds:.2f}s)."
        )
    if test_id == "T-11" and cases:
        props = _case_properties(test_id, cases)
        if "t11_coverage" in props:
            text += (
                f" Uncalibrated index on {props.get('t11_n_held_out')} held-out of "
                f"{props.get('t11_n_total')} cases: coverage {props['t11_coverage']}, "
                f"selective accuracy {props.get('t11_selective_accuracy')} "
                f"({props.get('t11_n_selective')} selected), ECE {props.get('t11_ece')}."
            )
    if test_id == "T-29" and cases:
        props = _case_properties(test_id, cases)
        if "t29_distinct_backends" in props:
            text += (
                f" {props.get('t29_transactions')} transactions over "
                f"PgBouncer using {props['t29_distinct_backends']} server backend(s), "
                f"{props.get('t29_backends_shared_by_tenants')} of them serving more than "
                "one tenant; "
                f"{props.get('t29_rolled_back')} rolled back, "
                f"{props.get('t29_foreign_inserts_blocked')} foreign-tenant inserts refused, "
                f"{props.get('t29_leaks')} leaks."
            )
    if test_id == "T-26" and outcome is not None:
        text += " " + _t26_text(t26)
    return f"{text} {note}".strip()


def _render_table(
    cases: list[JunitCase],
    *,
    lang: str,
    commit: str,
    run_label: str,
    t26: dict[str, object] | None = None,
) -> str:
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
        status = status_for(test_id, outcome, t26)
        if lang == "fr":
            status = STATUS_FR[status]
        measured = _measurement(test_id, outcome, cases, t26)
        lines.append(
            f"| {test_id} | {tier} | {criterion} | {measured} | {status} | "
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


def build_report(
    *,
    junit_paths: list[Path],
    run_id: str,
    run_url: str,
    commit: str,
    t26: dict[str, object] | None = None,
) -> str:
    cases: list[JunitCase] = []
    for path in junit_paths:
        cases.extend(_parse_junit(path))
    if not cases:
        raise ValueError("no JUnit test cases found; refusing to write an empty report")
    run_label = f"run {run_id}" if run_id else "local run (no CI run id)"
    counts: dict[str, int] = {}
    for test_id in CRITERIA:
        status = status_for(test_id, _outcome_for_test(test_id, cases), t26)
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
        _render_table(cases, lang="en", commit=commit, run_label=run_label, t26=t26),
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
        _render_table(cases, lang="fr", commit=commit, run_label=run_label, t26=t26),
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
    parser.add_argument("--t26-summary", type=Path, default=None)
    args = parser.parse_args()
    t26: dict[str, object] | None = None
    if args.t26_summary and args.t26_summary.is_file():
        t26 = json.loads(args.t26_summary.read_text(encoding="utf-8"))
    run_url = args.run_url
    if not run_url and args.run_id and os.environ.get("GITHUB_REPOSITORY"):
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        run_url = f"{server}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{args.run_id}"
    paths = [p for p in (args.junit_unit, args.junit_integration) if p]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(
        junit_paths=paths, run_id=args.run_id, run_url=run_url, commit=args.commit, t26=t26
    )
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
