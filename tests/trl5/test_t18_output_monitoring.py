from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleartrace_risk.output_monitor import OutputMonitor

pytestmark = pytest.mark.trl5

ROOT = Path(__file__).resolve().parents[2]
SEEDS = json.loads((ROOT / "tests" / "trl5" / "fixtures" / "t18_output_seeds.json").read_text())
DIMENSIONS = OutputMonitor.DIMENSIONS
# All seeds are hand-written; none comes from a public dataset.
SYNTHETIC_LABEL = "synthetic (hand-written, tools/generate_t18_seeds.py)"


def _failure_case(dimension: str, seed: dict) -> bool:
    monitor = OutputMonitor()
    if dimension == "accuracy":
        baseline = float(seed["baseline"])
        labels = list(seed["labels"])
        bad = list(seed["predictions"])
        return monitor.check_accuracy(baseline, bad, labels).detected
    if dimension == "fairness_gap":
        return monitor.check_fairness_gap(list(seed["preds"]), list(seed["sensitive"])).detected
    if dimension == "pii_leak":
        return monitor.check_pii_leak(list(seed["texts"])).detected
    if dimension == "en_fr":
        return monitor.check_en_fr(list(seed["en"]), list(seed["fr"])).detected
    if dimension == "safety":
        return monitor.check_safety(list(seed["flags"])).detected
    raise AssertionError(f"unknown dimension {dimension}")


def _clean_case(dimension: str, seed: dict) -> bool:
    monitor = OutputMonitor()
    if dimension == "accuracy":
        labels = list(seed["labels"][:4])
        preds = labels.copy()
        return monitor.check_accuracy(0.9, preds, labels).detected
    if dimension == "fairness_gap":
        preds = [1, 0, 1, 0]
        sensitive = ["A", "A", "B", "B"]
        return monitor.check_fairness_gap(preds, sensitive).detected
    if dimension == "pii_leak":
        return monitor.check_pii_leak(["no sensitive content"] * 4).detected
    if dimension == "en_fr":
        answers = ["same", "answer"]
        return monitor.check_en_fr(answers, answers).detected
    if dimension == "safety":
        return monitor.check_safety([False, False, False]).detected
    raise AssertionError(f"unknown dimension {dimension}")


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_t18_output_monitoring(dimension: str) -> None:
    failure_seeds = SEEDS[dimension]["failure"]
    clean_seeds = SEEDS[dimension]["clean"]
    assert len(failure_seeds) >= 50
    labels = {seed.get("dataset") for seed in failure_seeds + clean_seeds}
    assert labels == {SYNTHETIC_LABEL}, f"{dimension} seeds carry unexpected origin labels: {labels}"
    detected = sum(1 for seed in failure_seeds[:50] if _failure_case(dimension, seed))
    false_alarms = sum(1 for seed in clean_seeds[:50] if _clean_case(dimension, seed))
    assert detected >= 48, f"{dimension}: {detected}/50 failures detected"
    assert false_alarms <= 2, f"{dimension}: {false_alarms}/50 false alarms"
