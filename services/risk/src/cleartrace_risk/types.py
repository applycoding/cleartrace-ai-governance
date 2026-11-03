"""Shared types for the ClearTrace risk engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class MetricArea(StrEnum):
    DATA_QUALITY = "data_quality"
    DATA_DRIFT = "data_drift"
    PERSONAL_INFO = "personal_info"
    MODEL_PERFORMANCE = "model_performance"
    CALIBRATION = "calibration"
    FAIRNESS = "fairness"
    OUTPUT_QUALITY = "output_quality"
    CONSISTENCY = "consistency"
    SAFETY = "safety"
    OPERATIONS = "operations"


class ObservationStatus(StrEnum):
    OK = "ok"
    WARN = "warn"
    BREACH = "breach"


class RiskCategory(StrEnum):
    DATA = "data"
    MODEL = "model"
    OUTPUT = "output"
    SECURITY = "security"
    PRIVACY = "privacy"
    BIAS = "bias"
    SUPPLY_CHAIN = "supply_chain"


@dataclass(frozen=True)
class MetricSpec:
    code: str
    area: MetricArea
    name_en: str
    name_fr: str
    library: str
    default_warn: float | None
    default_breach: float
    higher_is_worse: bool = True
    unit: str = "ratio"


@dataclass
class ThresholdSpec:
    metric_code: str
    warn_value: float | None
    breach_value: float
    higher_is_worse: bool
    binding: bool
    linked_control_id: UUID | None
    name_en: str
    name_fr: str


@dataclass
class ObservationRecord:
    metric_code: str
    value: float
    status: ObservationStatus
    details: dict[str, Any] = field(default_factory=dict)
    window_start: str | None = None
    window_end: str | None = None


@dataclass
class BreachActionResult:
    observation: ObservationRecord
    alert_raised: bool
    control_outcome_changed: bool
    risk_raised: bool
    issue_id: UUID | None = None
    risk_id: UUID | None = None
    alert_id: UUID | None = None
    new_control_outcome: str | None = None
