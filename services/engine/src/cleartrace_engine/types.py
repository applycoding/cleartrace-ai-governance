from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceIssue(StrEnum):
    MISSING = "EVIDENCE_MISSING"
    STALE = "EVIDENCE_STALE"
    UNAUTHORIZED = "SUBMITTER_UNAUTHORIZED"


@dataclass(frozen=True)
class EvaluationError:
    code: str
    message_en: str
    message_fr: str


@dataclass(frozen=True)
class ObjectiveResult:
    objective_key: str
    applicable: bool
    passed: bool | None
    critical_gate: bool


@dataclass(frozen=True)
class ControlContext:
    control_id: str
    control_version: str
    requirement_en: str
    requirement_fr: str
    clause_ref: str
    source_url: str
    remediation_en: str
    remediation_fr: str


@dataclass(frozen=True)
class EvaluationInput:
    contract_version: str
    control: ControlContext
    system: dict[str, object]
    evidence: list[dict[str, object]]
    metrics: list[dict[str, object]]
    applicability_known: bool
    applicability: bool | None
    objective_results: list[ObjectiveResult]
    evaluation_errors: list[EvaluationError]
    evidence_issues: list[str]
    engine_bundle_digest: str
    used_llm: bool = False


@dataclass(frozen=True)
class EvaluationOutput:
    outcome_state: str
    reason_code: str
    certainty_index: float
    explanation_en: str
    explanation_fr: str
