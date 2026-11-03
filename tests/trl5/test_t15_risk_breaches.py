from __future__ import annotations

from uuid import uuid4

import pytest
from cleartrace_contracts.models import OutcomeState
from cleartrace_risk.breach import BreachProcessor, ControlOutcomeStore, RiskRegister
from cleartrace_risk.catalogue import catalogue_by_code
from cleartrace_risk.thresholds import build_observation
from cleartrace_risk.types import RiskCategory, ThresholdSpec


def _areas() -> list[tuple[str, str, RiskCategory]]:
    return [
        ("data.completeness.missing_rate", "data", RiskCategory.DATA),
        ("data.drift.psi", "data", RiskCategory.DATA),
        ("model.accuracy", "model", RiskCategory.MODEL),
        ("fairness.demographic_parity_diff", "model", RiskCategory.BIAS),
        ("privacy.pii.rate", "output", RiskCategory.PRIVACY),
        ("output.en_fr_agreement", "output", RiskCategory.OUTPUT),
    ]


@pytest.mark.trl5
def test_t15_binding_and_advisory_breaches() -> None:
    catalogue = catalogue_by_code()
    controls = ControlOutcomeStore()
    register = RiskRegister()
    processor = BreachProcessor(controls=controls, register=register)
    system_id = uuid4()

    binding_pass = 0
    for idx in range(30):
        area = _areas()[idx % len(_areas())]
        metric_code, _area_name, category = area
        spec = catalogue[metric_code]
        control_id = uuid4()
        controls.outcomes[(system_id, control_id)] = OutcomeState.MET
        value = spec.default_breach * 2 if spec.higher_is_worse else spec.default_breach / 2
        threshold = ThresholdSpec(
            metric_code=metric_code,
            warn_value=spec.default_warn,
            breach_value=spec.default_breach,
            higher_is_worse=spec.higher_is_worse,
            binding=True,
            linked_control_id=control_id,
            name_en=spec.name_en,
            name_fr=spec.name_fr,
        )
        observation = build_observation(
            metric_code,
            value,
            warn_value=threshold.warn_value,
            breach_value=threshold.breach_value,
            higher_is_worse=threshold.higher_is_worse,
        )
        result = processor.apply(
            system_id=system_id,
            threshold=threshold,
            observation=observation,
            category=category,
        )
        assert result.alert_raised
        assert result.control_outcome_changed
        assert result.risk_raised
        assert controls.get(system_id, control_id) == OutcomeState.NOT_MET
        binding_pass += 1

    advisory_pass = 0
    for idx in range(30):
        metric_code, _, category = _areas()[idx % len(_areas())]
        spec = catalogue[metric_code]
        control_id = uuid4()
        controls.outcomes[(system_id, control_id)] = OutcomeState.MET
        before_changes = len(controls.changes)
        value = spec.default_breach * 2 if spec.higher_is_worse else spec.default_breach / 2
        threshold = ThresholdSpec(
            metric_code=metric_code,
            warn_value=spec.default_warn,
            breach_value=spec.default_breach,
            higher_is_worse=spec.higher_is_worse,
            binding=False,
            linked_control_id=control_id,
            name_en=spec.name_en,
            name_fr=spec.name_fr,
        )
        observation = build_observation(
            metric_code,
            value,
            warn_value=threshold.warn_value,
            breach_value=threshold.breach_value,
            higher_is_worse=threshold.higher_is_worse,
        )
        result = processor.apply(
            system_id=system_id,
            threshold=threshold,
            observation=observation,
            category=category,
        )
        assert result.alert_raised
        assert not result.control_outcome_changed
        assert controls.get(system_id, control_id) == OutcomeState.MET
        assert len(controls.changes) == before_changes
        advisory_pass += 1

    assert binding_pass == 30
    assert advisory_pass == 30
    assert len(register.alerts) == 60
