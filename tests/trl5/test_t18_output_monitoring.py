from __future__ import annotations

import pytest
from cleartrace_risk.output_monitor import OutputMonitor

from tests.trl5.t18_seeds import (
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


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_t18_output_monitoring(dimension: str) -> None:
    monitor = OutputMonitor()
    detected = 0
    false_alarms = 0
    for seed in range(50):
        if dimension == "accuracy":
            preds, labels, baseline, meta = accuracy_failure(seed)
            assert "german" in meta.source_label or meta.synthetic_reason
            if monitor.check_accuracy(baseline, preds, labels).detected:
                detected += 1
            cp, cl, cb, clean_meta = accuracy_clean(seed)
            assert clean_meta.source_label
            if monitor.check_accuracy(cb, cp, cl).detected:
                false_alarms += 1
        elif dimension == "fairness_gap":
            preds, sensitive, meta = fairness_failure(seed)
            assert "adult" in meta.source_label
            if monitor.check_fairness_gap(preds, sensitive).detected:
                detected += 1
            cp, cs, clean_meta = fairness_clean(seed)
            assert clean_meta.source_label
            if monitor.check_fairness_gap(cp, cs).detected:
                false_alarms += 1
        elif dimension == "pii_leak":
            texts, meta = pii_failure(seed)
            assert meta.source_label == "synthetic"
            if monitor.check_pii_leak(texts).detected:
                detected += 1
            clean_texts, clean_meta = pii_clean(seed)
            assert clean_meta.synthetic_reason
            if monitor.check_pii_leak(clean_texts).detected:
                false_alarms += 1
        elif dimension == "en_fr":
            en, fr, meta = enfr_failure(seed)
            assert meta.synthetic_reason
            if monitor.check_en_fr(en, fr).detected:
                detected += 1
            ce, cf, clean_meta = enfr_clean(seed)
            assert clean_meta.source_label == "synthetic"
            if monitor.check_en_fr(ce, cf).detected:
                false_alarms += 1
        elif dimension == "safety":
            flags, meta = safety_failure(seed)
            assert meta.synthetic_reason
            if monitor.check_safety(flags).detected:
                detected += 1
            clean_flags, clean_meta = safety_clean(seed)
            assert clean_meta.source_label == "synthetic"
            if monitor.check_safety(clean_flags).detected:
                false_alarms += 1
        else:
            raise AssertionError(f"unknown dimension {dimension}")
    assert detected >= 48, f"{dimension}: {detected}/50 failures detected"
    assert false_alarms <= 2, f"{dimension}: {false_alarms}/50 false alarms"
