"""ClearTrace risk engine facade implementing the RiskEngine protocol."""

from __future__ import annotations

from uuid import UUID

from cleartrace_risk.breach import BreachProcessor, ControlOutcomeStore, RiskRegister
from cleartrace_risk.catalogue import STARTER_CATALOGUE, catalogue_by_code
from cleartrace_risk.data_quality_engine import DataQualityEngine
from cleartrace_risk.types import ThresholdSpec


class CleartraceRiskEngine:
    def __init__(self) -> None:
        self.catalogue = catalogue_by_code()
        self.controls = ControlOutcomeStore()
        self.register = RiskRegister()
        self.breach_processor = BreachProcessor(controls=self.controls, register=self.register)
        self.data_quality = DataQualityEngine()

    async def ingest_observations(self, tenant_id: UUID, batch: list[dict[str, object]]) -> None:
        del tenant_id
        for item in batch:
            metric_code = str(item["metric_code"])
            system_id = UUID(str(item["system_id"]))
            warn_raw = item.get("warn_value")
            warn_value = float(warn_raw) if warn_raw is not None else None  # type: ignore[arg-type]
            threshold = ThresholdSpec(
                metric_code=metric_code,
                warn_value=warn_value,
                breach_value=float(item["breach_value"]),  # type: ignore[arg-type]
                higher_is_worse=bool(item.get("higher_is_worse", True)),
                binding=bool(item.get("binding", False)),
                linked_control_id=UUID(str(item["linked_control_id"]))
                if item.get("linked_control_id")
                else None,
                name_en=str(item.get("name_en", metric_code)),
                name_fr=str(item.get("name_fr", metric_code)),
            )
            from cleartrace_risk.thresholds import build_observation

            details_raw = item.get("details")
            details = (
                {str(k): v for k, v in details_raw.items()}
                if isinstance(details_raw, dict)
                else {}
            )
            observation = build_observation(
                metric_code,
                float(item["value"]),  # type: ignore[arg-type]
                warn_value=threshold.warn_value,
                breach_value=threshold.breach_value,
                higher_is_worse=threshold.higher_is_worse,
                details=details,
            )
            self.breach_processor.apply(
                system_id=system_id,
                threshold=threshold,
                observation=observation,
                dataset_version=str(item.get("dataset_version", "unknown")),
                defect_type=str(item["defect_type"]) if item.get("defect_type") else None,
            )

    def starter_catalogue(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "code": spec.code,
                "area": spec.area.value,
                "name_en": spec.name_en,
                "name_fr": spec.name_fr,
                "library": spec.library,
                "default_warn": spec.default_warn,
                "default_breach": spec.default_breach,
                "higher_is_worse": spec.higher_is_worse,
                "unit": spec.unit,
            }
            for spec in STARTER_CATALOGUE
        )
