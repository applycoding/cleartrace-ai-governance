"""Binding versus advisory breach handling and risk register side effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cleartrace_contracts.models import OutcomeState

from cleartrace_risk.types import (
    BreachActionResult,
    ObservationRecord,
    ObservationStatus,
    RiskCategory,
    ThresholdSpec,
)


@dataclass
class ControlOutcomeStore:
    """In-memory control outcomes for TRL 5 and unit tests."""

    outcomes: dict[tuple[UUID, UUID], OutcomeState] = field(default_factory=dict)
    changes: list[tuple[UUID, UUID, OutcomeState, OutcomeState]] = field(default_factory=list)

    def get(self, system_id: UUID, control_id: UUID) -> OutcomeState:
        return self.outcomes.get((system_id, control_id), OutcomeState.MET)

    def set(self, system_id: UUID, control_id: UUID, outcome: OutcomeState) -> bool:
        key = (system_id, control_id)
        previous = self.outcomes.get(key, OutcomeState.MET)
        if previous == outcome:
            return False
        self.outcomes[key] = outcome
        self.changes.append((system_id, control_id, previous, outcome))
        return True


@dataclass
class RiskRegister:
    risks: dict[UUID, dict[str, object]] = field(default_factory=dict)
    alerts: list[dict[str, object]] = field(default_factory=list)
    issues: dict[UUID, dict[str, object]] = field(default_factory=dict)

    def raise_risk(
        self,
        *,
        system_id: UUID,
        category: RiskCategory,
        summary_en: str,
        summary_fr: str,
    ) -> UUID:
        risk_id = uuid4()
        self.risks[risk_id] = {
            "system_id": system_id,
            "category": category.value,
            "status": "draft",
            "summary_en": summary_en,
            "summary_fr": summary_fr,
        }
        return risk_id

    def raise_alert(
        self,
        *,
        system_id: UUID,
        binding: bool,
        message_en: str,
        message_fr: str,
        observation: ObservationRecord,
    ) -> UUID:
        alert_id = uuid4()
        self.alerts.append(
            {
                "id": alert_id,
                "system_id": system_id,
                "binding": binding,
                "message_en": message_en,
                "message_fr": message_fr,
                "metric_code": observation.metric_code,
                "value": observation.value,
            }
        )
        return alert_id

    def open_issue(
        self,
        *,
        system_id: UUID,
        dataset_version: str,
        defect_type: str,
        observation: ObservationRecord,
        linked_control_id: UUID | None,
        trace: dict[str, object],
    ) -> UUID:
        issue_id = uuid4()
        self.issues[issue_id] = {
            "system_id": system_id,
            "dataset_version": dataset_version,
            "defect_type": defect_type,
            "observation": observation,
            "linked_control_id": linked_control_id,
            "trace": trace,
            "status": "open",
        }
        return issue_id


class BreachProcessor:
    def __init__(
        self,
        *,
        controls: ControlOutcomeStore,
        register: RiskRegister,
    ) -> None:
        self._controls = controls
        self._register = register

    def apply(
        self,
        *,
        system_id: UUID,
        threshold: ThresholdSpec,
        observation: ObservationRecord,
        dataset_version: str = "synthetic",
        defect_type: str | None = None,
        category: RiskCategory = RiskCategory.DATA,
    ) -> BreachActionResult:
        if observation.status not in {ObservationStatus.WARN, ObservationStatus.BREACH}:
            return BreachActionResult(
                observation=observation,
                alert_raised=False,
                control_outcome_changed=False,
                risk_raised=False,
            )

        alert_id = self._register.raise_alert(
            system_id=system_id,
            binding=threshold.binding,
            message_en=f"Threshold crossed for {threshold.metric_code}",
            message_fr=f"Seuil dépassé pour {threshold.metric_code}",
            observation=observation,
        )

        control_changed = False
        risk_raised = False
        issue_id: UUID | None = None
        new_outcome: str | None = None

        if threshold.binding and threshold.linked_control_id is not None:
            changed = self._controls.set(
                system_id,
                threshold.linked_control_id,
                OutcomeState.NOT_MET,
            )
            control_changed = changed
            risk_raised = True
            risk_id = self._register.raise_risk(
                system_id=system_id,
                category=category,
                summary_en=f"Binding breach on {threshold.metric_code}",
                summary_fr=f"Dépassement contraignant sur {threshold.metric_code}",
            )
            issue_id = self._register.open_issue(
                system_id=system_id,
                dataset_version=dataset_version,
                defect_type=defect_type or threshold.metric_code,
                observation=observation,
                linked_control_id=threshold.linked_control_id,
                trace={
                    "metric_code": observation.metric_code,
                    "value": observation.value,
                    "status": observation.status.value,
                    "risk_id": str(risk_id),
                },
            )
            new_outcome = OutcomeState.NOT_MET.value
        elif defect_type is not None:
            issue_id = self._register.open_issue(
                system_id=system_id,
                dataset_version=dataset_version,
                defect_type=defect_type,
                observation=observation,
                linked_control_id=threshold.linked_control_id,
                trace={
                    "metric_code": observation.metric_code,
                    "value": observation.value,
                    "status": observation.status.value,
                },
            )

        return BreachActionResult(
            observation=observation,
            alert_raised=True,
            control_outcome_changed=control_changed,
            risk_raised=risk_raised,
            issue_id=issue_id,
            alert_id=alert_id,
            new_control_outcome=new_outcome,
        )
