from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("trl5_report", ROOT / "tools" / "trl5_report.py")
assert _spec is not None and _spec.loader is not None
trl5_report = importlib.util.module_from_spec(_spec)
sys.modules["trl5_report"] = trl5_report
_spec.loader.exec_module(trl5_report)


def _junit(tmp_path: Path, cases: list[tuple[str, str, str]]) -> Path:
    results = {
        "pass": "",
        "fail": "<failure message='x'/>",
        "skip": "<skipped type='pytest.xfail'/>",
    }
    body = []
    for module, name, result in cases:
        inner = results[result]
        body.append(
            f'<testcase classname="tests.trl5.{module}" name="{name}" time="0.1">{inner}</testcase>'
        )
    path = tmp_path / "junit.xml"
    path.write_text(
        f"<testsuites><testsuite>{''.join(body)}</testsuite></testsuites>", encoding="utf-8"
    )
    return path


def _status(tmp_path: Path, test_id: str, cases: list[tuple[str, str, str]]) -> str:
    parsed = trl5_report._parse_junit(_junit(tmp_path, cases))
    hint = trl5_report.CRITERIA[test_id][2]
    return str(trl5_report.status_for(test_id, trl5_report._outcome_for(hint, parsed)))


def test_pass_only_when_every_case_ran_and_passed(tmp_path: Path) -> None:
    ok = [("test_t01_policy_change", "a", "pass"), ("test_t01_policy_change", "b", "pass")]
    assert _status(tmp_path, "T-01", ok) == "pass"
    one_failed = [*ok, ("test_t01_policy_change", "c", "fail")]
    assert _status(tmp_path, "T-01", one_failed) == "fail"


def test_missing_or_skipped_cases_are_not_pass(tmp_path: Path) -> None:
    assert _status(tmp_path, "T-01", [("test_t02_connectors_register", "a", "pass")]) == "not run"
    assert _status(tmp_path, "T-01", [("test_t01_policy_change", "a", "skip")]) == "not run"
    mixed = [("test_t01_policy_change", "a", "pass"), ("test_t01_policy_change", "b", "skip")]
    assert _status(tmp_path, "T-01", mixed) == "partial"


def test_t13_green_run_is_pass_with_independent_oracle(tmp_path: Path) -> None:
    """T-13 stays out of PARTIAL_NOTES once cases are distinct and oracle-backed."""
    assert "T-13" not in trl5_report.PARTIAL_NOTES
    cases = [("test_t13_five_states", "test_t13_golden_outcome", "pass")]
    assert _status(tmp_path, "T-13", cases) == "pass"



def test_t11_is_partial_and_reports_measured_numbers(tmp_path: Path) -> None:
    assert _status(tmp_path, "T-11", [("test_t11_certainty_index", "a", "pass")]) == "partial"
    path = tmp_path / "junit.xml"
    path.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="tests.trl5.test_t11_certainty_index" name="m" time="0.1">'
        '<properties><property name="t11_coverage" value="0.50"/>'
        '<property name="t11_ece" value="0.40"/></properties></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    text = trl5_report.build_report(junit_paths=[path], run_id="1", run_url="", commit="x")
    assert "Uncalibrated index" in text and "coverage 0.50" in text and "ECE 0.40" in text
    assert "| calibrated" not in text


def test_t26_needs_a_passing_gate_summary(tmp_path: Path) -> None:
    parsed = trl5_report._parse_junit(
        _junit(tmp_path, [("test_t26_security_gate", "a", "pass")])
    )
    outcome = trl5_report._outcome_for_test("T-26", parsed)
    assert trl5_report.status_for("T-26", outcome) == "fail"
    assert trl5_report.status_for("T-26", outcome, {"gate_passed": False}) == "fail"
    assert trl5_report.status_for("T-26", outcome, {"gate_passed": True}) == "pass"


def test_t21_and_t29_modules_can_reach_pass(tmp_path: Path) -> None:
    assert (
        _status(tmp_path, "T-21", [("test_t21_multi_tenant", "a", "pass")]) == "pass"
    )
    assert (
        _status(tmp_path, "T-29", [("test_t29_pooled_leak", "a", "pass")]) == "pass"
    )


def test_unimplemented_ids(tmp_path: Path) -> None:
    assert _status(tmp_path, "T-27", []) == "deferred"


def test_report_names_run_and_commit(tmp_path: Path) -> None:
    path = _junit(tmp_path, [("test_t01_policy_change", "a", "pass")])
    text = trl5_report.build_report(junit_paths=[path], run_id="123", run_url="", commit="abc123")
    assert "run 123" in text
    assert "`abc123`" in text


def test_empty_junit_is_refused(tmp_path: Path) -> None:
    path = _junit(tmp_path, [])
    with pytest.raises(ValueError):
        trl5_report.build_report(junit_paths=[path], run_id="1", run_url="", commit="x")
