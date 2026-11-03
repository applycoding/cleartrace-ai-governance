from __future__ import annotations

import pytest
from cleartrace_risk.data_quality_engine import DataQualityEngine
from cleartrace_risk.datasets import sample_clean_window, sample_defective_window

DEFECT_TYPES = ("completeness", "schema", "psi", "ks")
SOURCES = ("adult", "german")


@pytest.mark.trl5
@pytest.mark.parametrize("defect_type", DEFECT_TYPES)
@pytest.mark.parametrize("source", SOURCES)
def test_t16_data_defect_detection(defect_type: str, source: str) -> None:
    engine = DataQualityEngine()
    defective_hits = 0
    for seed in range(50):
        window = sample_defective_window(defect_type, source, seed=10_000 + seed)
        if engine.window_is_defective(window, defect_type):
            defective_hits += 1
            flags = engine.evaluate_window(window)
            matching = [f for f in flags if f.defect_type == defect_type and f.flagged]
            assert matching, "flag must include traceable issue metadata"
            assert matching[0].trace.get("status") in {"warn", "breach"}

    clean_false = 0
    for seed in range(50):
        window = sample_clean_window(source, seed=20_000 + seed, rows=120)
        if not engine.window_is_clean(window):
            clean_false += 1

    assert defective_hits >= 48, f"{defect_type}/{source}: {defective_hits}/50"
    assert clean_false <= 2, f"{defect_type}/{source}: {clean_false}/50 false positives"
