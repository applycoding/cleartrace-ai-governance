"""Model performance, calibration, and fairness evaluators."""

from __future__ import annotations

import numpy as np
from fairlearn.metrics import demographic_parity_difference
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def accuracy_delta(baseline_accuracy: float, y_true: list[int], y_pred: list[int]) -> float:
    current = float(accuracy_score(y_true, y_pred))
    return baseline_accuracy - current


def f1_score_value(y_true: list[int], y_pred: list[int]) -> float:
    return float(f1_score(y_true, y_pred, zero_division=0))


def auc_value(y_true: list[int], y_score: list[float]) -> float:
    if len(set(y_true)) < 2:
        return 0.5
    return float(roc_auc_score(y_true, y_score))


def expected_calibration_error(y_true: list[int], y_prob: list[float], *, bins: int = 10) -> float:
    prob = np.asarray(y_prob, dtype=float)
    labels = np.asarray(y_true, dtype=int)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for idx in range(bins):
        mask = (prob >= edges[idx]) & (prob < edges[idx + 1])
        if not np.any(mask):
            continue
        acc = labels[mask].mean()
        conf = prob[mask].mean()
        ece += abs(acc - conf) * mask.mean()
    return float(ece)


def fairness_demographic_parity(
    y_true: list[int], y_pred: list[int], sensitive: list[str]
) -> float:
    return float(
        demographic_parity_difference(
            y_true,
            y_pred,
            sensitive_features=sensitive,
        )
    )


def disparate_impact_ratio(y_pred: list[int], sensitive: list[str]) -> float:
    groups: dict[str, list[int]] = {}
    for label, pred in zip(sensitive, y_pred, strict=True):
        groups.setdefault(label, []).append(pred)
    rates = [sum(values) / max(len(values), 1) for values in groups.values()]
    if not rates:
        return 1.0
    return float(min(rates) / max(max(rates), 1e-9))
