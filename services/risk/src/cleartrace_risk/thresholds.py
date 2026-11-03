"""Evaluate observations against warn/breach thresholds."""

from __future__ import annotations

from cleartrace_risk.types import ObservationRecord, ObservationStatus


def classify_value(
    value: float,
    *,
    warn_value: float | None,
    breach_value: float,
    higher_is_worse: bool,
) -> ObservationStatus:
    if higher_is_worse:
        if value >= breach_value:
            return ObservationStatus.BREACH
        if warn_value is not None and value >= warn_value:
            return ObservationStatus.WARN
        return ObservationStatus.OK
    if value <= breach_value:
        return ObservationStatus.BREACH
    if warn_value is not None and value <= warn_value:
        return ObservationStatus.WARN
    return ObservationStatus.OK


def build_observation(
    metric_code: str,
    value: float,
    *,
    warn_value: float | None,
    breach_value: float,
    higher_is_worse: bool,
    details: dict[str, object] | None = None,
) -> ObservationRecord:
    status = classify_value(
        value,
        warn_value=warn_value,
        breach_value=breach_value,
        higher_is_worse=higher_is_worse,
    )
    return ObservationRecord(
        metric_code=metric_code,
        value=value,
        status=status,
        details=dict(details or {}),
    )
