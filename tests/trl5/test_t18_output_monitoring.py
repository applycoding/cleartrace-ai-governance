from __future__ import annotations

import pytest
from cleartrace_risk.output_monitor import OutputMonitor

DIMENSIONS = OutputMonitor.DIMENSIONS


def _seeded_failure(dimension: str, seed: int) -> bool:
    monitor = OutputMonitor()
    if dimension == "accuracy":
        baseline = 0.95
        labels = [1, 0, 1, 0, 1, 0, 1, 0]
        bad = [0] * len(labels)
        return monitor.check_accuracy(baseline, bad, labels).detected
    if dimension == "fairness_gap":
        preds = [1] * 12 + [0] * 12
        sensitive = ["A"] * 12 + ["B"] * 12
        return monitor.check_fairness_gap(preds, sensitive).detected
    if dimension == "pii_leak":
        texts = ["clean answer"] * 5 + ["contact me at user@example.com"]
        return monitor.check_pii_leak(texts).detected
    if dimension == "en_fr":
        en = ["yes", "no", "approved"]
        fr = ["yes", "non", "approved"]
        return monitor.check_en_fr(en, fr).detected
    if dimension == "safety":
        flags = [False, False, True, False, True]
        return monitor.check_safety(flags).detected
    raise AssertionError(f"unknown dimension {dimension}")


def _seeded_clean(dimension: str) -> bool:
    monitor = OutputMonitor()
    if dimension == "accuracy":
        labels = [1, 0, 1, 0]
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


@pytest.mark.trl5
@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_t18_output_monitoring(dimension: str) -> None:
    detected = sum(1 for seed in range(50) if _seeded_failure(dimension, seed))
    false_alarms = sum(1 for _ in range(50) if _seeded_clean(dimension))
    assert detected >= 48, f"{dimension}: {detected}/50 failures detected"
    assert false_alarms <= 2, f"{dimension}: {false_alarms}/50 false alarms"
