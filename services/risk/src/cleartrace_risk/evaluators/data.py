"""Data-quality and drift evaluators (Evidently, SciPy, own SQL-style checks)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def missing_rate(frame: pd.DataFrame) -> float:
    if frame.empty:
        return 0.0
    return float(frame.isna().mean().mean())


def schema_violation_count(frame: pd.DataFrame, schema: dict[str, object]) -> float:
    violations = 0
    for column, kind in schema.items():
        if str(column).endswith("_allowed"):
            continue
        if column not in frame.columns:
            violations += len(frame)
            continue
        series = frame[column]
        if kind == "numeric":
            coerced = pd.to_numeric(series, errors="coerce")
            violations += int(coerced.isna().sum() - series.isna().sum())
        elif kind == "category":
            allowed = schema.get(f"{column}_allowed", [])
            if isinstance(allowed, list) and allowed:
                violations += int((~series.isin(allowed) & series.notna()).sum())
    return float(violations)


def population_stability_index(
    reference: pd.Series, current: pd.Series, *, buckets: int = 10
) -> float:
    ref = reference.dropna()
    cur = current.dropna()
    if ref.empty or cur.empty:
        return 0.0
    try:
        ref_values = ref.astype(float)
        cur_values = pd.to_numeric(cur, errors="coerce").dropna()
    except (TypeError, ValueError):
        return 0.0
    if cur_values.empty:
        return 0.0
    quantiles = np.linspace(0, 1, buckets + 1)
    edges = np.unique(np.quantile(ref_values, quantiles))
    if len(edges) < 2:
        return 0.0
    ref_counts, _ = np.histogram(ref_values, bins=edges)
    cur_counts, _ = np.histogram(cur_values, bins=edges)
    ref_pct = ref_counts / max(ref_counts.sum(), 1)
    cur_pct = cur_counts / max(cur_counts.sum(), 1)
    eps = 1e-6
    psi = float(np.sum((cur_pct - ref_pct) * np.log((cur_pct + eps) / (ref_pct + eps))))
    return max(psi, 0.0)


def ks_min_pvalue(reference: pd.DataFrame, current: pd.DataFrame) -> float:
    pvalues: list[float] = []
    for column in reference.columns:
        if column not in current.columns:
            continue
        ref = reference[column].dropna()
        cur = current[column].dropna()
        if len(ref) < 5 or len(cur) < 5:
            continue
        if pd.api.types.is_numeric_dtype(ref):
            stat = stats.ks_2samp(ref.astype(float), cur.astype(float))
            pvalues.append(float(stat.pvalue))
    if not pvalues:
        return 1.0
    sorted_p = np.sort(pvalues)
    m = len(sorted_p)
    adjusted = [min(1.0, p * m / (idx + 1)) for idx, p in enumerate(sorted_p)]
    return float(min(adjusted))


def evidently_data_summary(reference: pd.DataFrame, current: pd.DataFrame) -> dict[str, Any]:
    """Return a compact summary; Evidently is used when installed for drift reports."""
    summary: dict[str, Any] = {
        "reference_rows": len(reference),
        "current_rows": len(current),
        "missing_rate": missing_rate(current),
    }
    try:
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=reference, current_data=current)
        summary["evidently"] = report.as_dict()
    except Exception as exc:  # noqa: BLE001 — optional enrich only
        summary["evidently_error"] = str(exc)
    return summary
