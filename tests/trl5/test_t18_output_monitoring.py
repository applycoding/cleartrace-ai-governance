from __future__ import annotations

import json

import pytest
from cleartrace_risk.output_monitor import OutputMonitor

from tests.trl5.t18_seeds import (
    EXPECTED_LABELS,
    accuracy_clean,
    accuracy_failure,
    enfr_clean,
    enfr_failure,
    fairness_clean,
    fairness_failure,
    pii_clean,
    pii_failure,
    safety_clean,
    safety_failure,
)

pytestmark = pytest.mark.trl5

DIMENSIONS = OutputMonitor.DIMENSIONS


def _seed(dimension: str, seed: int) -> tuple[bool, bool, str, str, str]:
    """Return (failure detected, clean flagged, failure label, clean label, failure input)."""
    monitor = OutputMonitor()
    if dimension == "accuracy":
        preds, labels, baseline, meta = accuracy_failure(seed)
        cp, cl, cb, clean_meta = accuracy_clean(seed)
        hit = monitor.check_accuracy(baseline, preds, labels).detected
        alarm = monitor.check_accuracy(cb, cp, cl).detected
        key = json.dumps([preds, labels, baseline])
    elif dimension == "fairness_gap":
        preds, sensitive, meta = fairness_failure(seed)
        cp, cs, clean_meta = fairness_clean(seed)
        hit = monitor.check_fairness_gap(preds, sensitive).detected
        alarm = monitor.check_fairness_gap(cp, cs).detected
        key = json.dumps([preds, sensitive])
    elif dimension == "pii_leak":
        texts, meta = pii_failure(seed)
        clean_texts, clean_meta = pii_clean(seed)
        hit = monitor.check_pii_leak(texts).detected
        alarm = monitor.check_pii_leak(clean_texts).detected
        key = json.dumps(texts)
    elif dimension == "en_fr":
        en, fr, meta = enfr_failure(seed)
        ce, cf, clean_meta = enfr_clean(seed)
        hit = monitor.check_en_fr(en, fr).detected
        alarm = monitor.check_en_fr(ce, cf).detected
        key = json.dumps([en, fr])
    elif dimension == "safety":
        flags, meta = safety_failure(seed)
        clean_flags, clean_meta = safety_clean(seed)
        hit = monitor.check_safety(flags).detected
        alarm = monitor.check_safety(clean_flags).detected
        key = json.dumps(flags)
    else:
        raise AssertionError(f"unknown dimension {dimension}")
    return hit, alarm, meta.source_label, clean_meta.source_label, key


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_t18_output_monitoring(dimension: str, record_property: pytest.RecordProperty) -> None:
    results = [_seed(dimension, seed) for seed in range(50)]
    labels = {r[2] for r in results} | {r[3] for r in results}
    assert labels == {EXPECTED_LABELS[dimension]}, f"{dimension} seeds carry wrong source labels: {labels}"
    detected = sum(1 for r in results if r[0])
    false_alarms = sum(1 for r in results if r[1])
    distinct = len({r[4] for r in results})
    record_property("t18_detected", f"{dimension}={detected}/50")
    record_property("t18_false_alarms", f"{dimension}={false_alarms}/50")
    record_property("t18_distinct_failure_inputs", f"{dimension}={distinct}")
    record_property("t18_source", f"{dimension}={EXPECTED_LABELS[dimension]}")
    assert detected >= 48, f"{dimension}: {detected}/50 failures detected"
    assert false_alarms <= 2, f"{dimension}: {false_alarms}/50 false alarms"
