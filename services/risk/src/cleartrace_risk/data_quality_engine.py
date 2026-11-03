"""End-to-end data window evaluation for EO-16."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cleartrace_risk.catalogue import catalogue_by_code
from cleartrace_risk.datasets import DatasetWindow
from cleartrace_risk.evaluators import data as data_eval
from cleartrace_risk.thresholds import build_observation
from cleartrace_risk.types import ObservationStatus


@dataclass(frozen=True)
class DataWindowFlag:
    flagged: bool
    defect_type: str | None
    observation_metric: str
    trace: dict[str, object]


class DataQualityEngine:
    DEFECT_METRICS = {
        "completeness": "data.completeness.missing_rate",
        "schema": "data.schema.conformance_violations",
        "psi": "data.drift.psi",
        "ks": "data.drift.ks_pvalue",
    }

    def evaluate_window(self, window: DatasetWindow) -> list[DataWindowFlag]:
        catalogue = catalogue_by_code()
        flags: list[DataWindowFlag] = []
        missing = data_eval.missing_rate(window.current)
        obs = build_observation(
            self.DEFECT_METRICS["completeness"],
            missing,
            warn_value=catalogue[self.DEFECT_METRICS["completeness"]].default_warn,
            breach_value=catalogue[self.DEFECT_METRICS["completeness"]].default_breach,
            higher_is_worse=True,
            details={"missing_rate": missing},
        )
        flags.append(
            DataWindowFlag(
                flagged=obs.status != ObservationStatus.OK,
                defect_type="completeness" if obs.status != ObservationStatus.OK else None,
                observation_metric=obs.metric_code,
                trace={"value": missing, "status": obs.status.value},
            )
        )

        violations = data_eval.schema_violation_count(window.current, window.schema)
        obs_schema = build_observation(
            self.DEFECT_METRICS["schema"],
            violations,
            warn_value=None,
            breach_value=1.0,
            higher_is_worse=True,
            details={"violations": violations},
        )
        flags.append(
            DataWindowFlag(
                flagged=obs_schema.status != ObservationStatus.OK,
                defect_type="schema" if obs_schema.status != ObservationStatus.OK else None,
                observation_metric=obs_schema.metric_code,
                trace={"violations": violations, "status": obs_schema.status.value},
            )
        )

        numeric_cols = [
            col
            for col in window.reference.columns
            if col in window.current.columns
            and pd.api.types.is_numeric_dtype(window.reference[col])
        ]
        if numeric_cols:
            col = numeric_cols[0]
            psi = data_eval.population_stability_index(window.reference[col], window.current[col])
            obs_psi = build_observation(
                self.DEFECT_METRICS["psi"],
                psi,
                warn_value=catalogue[self.DEFECT_METRICS["psi"]].default_warn,
                breach_value=catalogue[self.DEFECT_METRICS["psi"]].default_breach,
                higher_is_worse=True,
                details={"column": col, "psi": psi},
            )
            flags.append(
                DataWindowFlag(
                    flagged=obs_psi.status != ObservationStatus.OK,
                    defect_type="psi" if obs_psi.status != ObservationStatus.OK else None,
                    observation_metric=obs_psi.metric_code,
                    trace={"column": col, "psi": psi, "status": obs_psi.status.value},
                )
            )

            pvalue = data_eval.ks_min_pvalue(window.reference, window.current)
            obs_ks = build_observation(
                self.DEFECT_METRICS["ks"],
                pvalue,
                warn_value=catalogue[self.DEFECT_METRICS["ks"]].default_warn,
                breach_value=catalogue[self.DEFECT_METRICS["ks"]].default_breach,
                higher_is_worse=False,
                details={"min_pvalue": pvalue},
            )
            flags.append(
                DataWindowFlag(
                    flagged=obs_ks.status != ObservationStatus.OK,
                    defect_type="ks" if obs_ks.status != ObservationStatus.OK else None,
                    observation_metric=obs_ks.metric_code,
                    trace={"min_pvalue": pvalue, "status": obs_ks.status.value},
                )
            )
        return flags

    def window_is_defective(self, window: DatasetWindow, defect_type: str) -> bool:
        flags = self.evaluate_window(window)
        return any(flag.defect_type == defect_type and flag.flagged for flag in flags)

    def window_is_clean(self, window: DatasetWindow) -> bool:
        flags = self.evaluate_window(window)
        return not any(flag.flagged for flag in flags)
