from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationReport:
    coverage: float
    selective_accuracy: float
    ece: float
    calibrated: bool
    n_total: int
    n_selective: int
    n_held_out: int


def expected_calibration_error(
    y_true: list[int],
    y_prob: list[float],
    *,
    bins: int = 10,
) -> float:
    """ECE for binary correctness labels and certainty scores in [0, 1]."""
    if not y_true:
        return 0.0
    if len(y_true) != len(y_prob):
        msg = "y_true and y_prob length mismatch"
        raise ValueError(msg)
    edges = [idx / bins for idx in range(bins + 1)]
    total = float(len(y_true))
    ece = 0.0
    for idx in range(bins):
        low, high = edges[idx], edges[idx + 1]
        mask = [
            i
            for i, prob in enumerate(y_prob)
            if (prob >= low and (prob < high or (idx == bins - 1 and prob <= high)))
        ]
        if not mask:
            continue
        acc = sum(y_true[i] for i in mask) / len(mask)
        conf = sum(y_prob[i] for i in mask) / len(mask)
        ece += abs(acc - conf) * (len(mask) / total)
    return round(ece, 4)


def selective_accuracy(
    y_true: list[int],
    y_prob: list[float],
    *,
    coverage_threshold: float = 0.50,
) -> tuple[float, float, int]:
    """Return (coverage, selective_accuracy, selective_count)."""
    if not y_true:
        return 0.0, 0.0, 0
    selective_idx = [i for i, p in enumerate(y_prob) if p >= coverage_threshold]
    coverage = len(selective_idx) / len(y_true)
    if not selective_idx:
        return coverage, 0.0, 0
    correct = sum(y_true[i] for i in selective_idx)
    return coverage, correct / len(selective_idx), len(selective_idx)


def calibration_report(
    y_true: list[int],
    y_prob: list[float],
    *,
    held_out_fraction: float = 0.2,
    coverage_threshold: float = 0.50,
    max_ece: float = 0.06,
    min_coverage: float = 0.60,
    min_selective_accuracy: float = 0.94,
) -> CalibrationReport:
    if not y_true:
        return CalibrationReport(0.0, 0.0, 0.0, False, 0, 0, 0)
    split = max(1, int(len(y_true) * held_out_fraction))
    held_y = y_true[-split:]
    held_p = y_prob[-split:]
    cov, sel_acc, n_sel = selective_accuracy(held_y, held_p, coverage_threshold=coverage_threshold)
    ece = expected_calibration_error(held_y, held_p)
    calibrated = (
        ece <= max_ece and cov >= min_coverage and sel_acc >= min_selective_accuracy
    )
    return CalibrationReport(
        coverage=round(cov, 4),
        selective_accuracy=round(sel_acc, 4),
        ece=ece,
        calibrated=calibrated,
        n_total=len(y_true),
        n_selective=n_sel,
        n_held_out=len(held_y),
    )
