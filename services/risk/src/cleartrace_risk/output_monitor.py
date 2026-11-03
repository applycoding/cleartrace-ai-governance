"""Output monitoring orchestrator for EO-18 dimensions."""

from __future__ import annotations

from dataclasses import dataclass

from cleartrace_risk.catalogue import catalogue_by_code
from cleartrace_risk.evaluators import output as output_eval
from cleartrace_risk.thresholds import build_observation


@dataclass(frozen=True)
class OutputCheckResult:
    dimension: str
    detected: bool
    value: float


class OutputMonitor:
    DIMENSIONS = ("accuracy", "fairness_gap", "pii_leak", "en_fr", "safety")

    def check_accuracy(
        self, baseline: float, predictions: list[int], labels: list[int]
    ) -> OutputCheckResult:
        catalogue = catalogue_by_code()
        spec = catalogue["model.accuracy"]
        delta = output_eval.output_accuracy_drop(baseline, predictions, labels)
        obs = build_observation(
            "model.accuracy",
            delta,
            warn_value=spec.default_warn,
            breach_value=spec.default_breach,
            higher_is_worse=True,
        )
        return OutputCheckResult("accuracy", obs.status != "ok", delta)

    def check_fairness_gap(self, y_pred: list[int], sensitive: list[str]) -> OutputCheckResult:
        catalogue = catalogue_by_code()
        gap = output_eval.fairness_gap(y_pred, sensitive)
        obs = build_observation(
            "fairness.demographic_parity_diff",
            gap,
            warn_value=catalogue["fairness.demographic_parity_diff"].default_warn,
            breach_value=catalogue["fairness.demographic_parity_diff"].default_breach,
            higher_is_worse=True,
        )
        return OutputCheckResult("fairness_gap", obs.status != "ok", gap)

    def check_pii_leak(self, texts: list[str]) -> OutputCheckResult:
        catalogue = catalogue_by_code()
        rate = output_eval.pii_leak_rate(texts)
        obs = build_observation(
            "privacy.pii.rate",
            rate,
            warn_value=None,
            breach_value=catalogue["privacy.pii.rate"].default_breach,
            higher_is_worse=True,
        )
        return OutputCheckResult("pii_leak", obs.status != "ok", rate)

    def check_en_fr(self, en_answers: list[str], fr_answers: list[str]) -> OutputCheckResult:
        catalogue = catalogue_by_code()
        agreement = output_eval.en_fr_agreement(en_answers, fr_answers)
        obs = build_observation(
            "output.en_fr_agreement",
            agreement,
            warn_value=catalogue["output.en_fr_agreement"].default_warn,
            breach_value=catalogue["output.en_fr_agreement"].default_breach,
            higher_is_worse=False,
        )
        return OutputCheckResult("en_fr", obs.status != "ok", agreement)

    def check_safety(self, success_flags: list[bool]) -> OutputCheckResult:
        catalogue = catalogue_by_code()
        rate = output_eval.safety_attack_success_rate(success_flags)
        obs = build_observation(
            "safety.attack_success_rate",
            rate,
            warn_value=catalogue["safety.attack_success_rate"].default_warn,
            breach_value=catalogue["safety.attack_success_rate"].default_breach,
            higher_is_worse=True,
        )
        return OutputCheckResult("safety", obs.status != "ok", rate)
