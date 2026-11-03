# T-11 adjudication rules (UCI fixtures)

Labels for the T-11 adjudicated finding set are derived deterministically from the public UCI Adult and Statlog German Credit windows used in T-16 (`cleartrace_risk.datasets`).

## Adjudicated outcome (ground truth)

For each window `(source, seed)`:

1. Build a defective window with `sample_defective_window(defect_type, source, seed=10_000 + seed)` for `defect_type` in `{completeness, schema}` rotating by `seed % 2`.
2. If `DataQualityEngine.window_is_defective(window, defect_type)` is true, the adjudicated outcome is **`not_met`**.
3. Otherwise build a clean window with `sample_clean_window(source, seed=20_000 + seed, rows=120)` and adjudicated outcome is **`met`**.

Document family is `source` (`adult` or `german`). EN and FR explanation templates are both evaluated (same numeric index; bilingual bands checked separately).

## Automated outcome

For each case, build an `EvaluationInput` with:

- One objective `data_quality_gate` marked `passed=(adjudicated == met)`.
- `evidence_issues` containing `EVIDENCE_MISSING` when adjudicated is `not_met` and the defect type is `completeness`; empty otherwise.

Run `evaluate_control` for the automated outcome and `certainty_index_v0` on the same payload.

## Calibration metrics (blueprint section 18)

Event: automated outcome equals adjudicated outcome.

- **Coverage:** fraction of held-out cases with certainty index ≥ 0.50 (medium/high band).
- **Selective accuracy:** accuracy of the event on held-out cases with index ≥ 0.50.
- **ECE:** expected calibration error on held-out cases treating index as confidence in the event.

Claim **calibrated** only if ECE ≤ 0.06, coverage ≥ 60%, selective accuracy ≥ 94%; otherwise report as an **uncalibrated index** (certainty index v0).
