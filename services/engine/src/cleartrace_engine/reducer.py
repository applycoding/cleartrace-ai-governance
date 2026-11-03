from __future__ import annotations

from cleartrace_contracts.models import OutcomeState

from cleartrace_engine.types import EvaluationError, ObjectiveResult

REASON_APPLICABILITY_FALSE = "NOT_APPLICABLE"
REASON_NO_APPLICABLE_OBJECTIVES = "NO_APPLICABLE_OBJECTIVES"
REASON_CRITICAL_GATE_FAILED = "CRITICAL_GATE_FAILED"
REASON_EVIDENCE_MISSING = "EVIDENCE_MISSING"
REASON_EVIDENCE_STALE = "EVIDENCE_STALE"
REASON_SUBMITTER_UNAUTHORIZED = "SUBMITTER_UNAUTHORIZED"
REASON_APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
REASON_EVAL_ERROR = "EVAL_ERROR"
REASON_MIXED_OBJECTIVES = "MIXED_OBJECTIVE_RESULTS"
REASON_ALL_MET = "ALL_OBJECTIVES_MET"
REASON_OBJECTIVES_FAILED = "OBJECTIVES_FAILED"


def reduce_outcome(
    *,
    applicability_known: bool,
    applicability: bool | None,
    objective_results: list[ObjectiveResult],
    evaluation_errors: list[EvaluationError],
    evidence_issues: list[str],
) -> tuple[OutcomeState, str]:
    """Apply blueprint section 6.2 precedence (first matching rule wins)."""
    if applicability is False:
        return OutcomeState.NOT_APPLICABLE, REASON_APPLICABILITY_FALSE

    applicable = [o for o in objective_results if o.applicable]
    if not applicable and applicability is True:
        return OutcomeState.NOT_APPLICABLE, REASON_NO_APPLICABLE_OBJECTIVES

    for obj in applicable:
        if obj.critical_gate and obj.passed is False:
            return OutcomeState.NOT_MET, REASON_CRITICAL_GATE_FAILED

    blocking_reasons: list[str] = []
    if not applicability_known or applicability is None:
        blocking_reasons.append(REASON_APPLICABILITY_UNKNOWN)
    blocking_reasons.extend(e.code for e in evaluation_errors)
    blocking_reasons.extend(evidence_issues)
    if blocking_reasons:
        code = blocking_reasons[0]
        if code == REASON_EVIDENCE_STALE:
            return OutcomeState.UNABLE_TO_DETERMINE, REASON_EVIDENCE_STALE
        if code == REASON_SUBMITTER_UNAUTHORIZED:
            return OutcomeState.UNABLE_TO_DETERMINE, REASON_SUBMITTER_UNAUTHORIZED
        if code == REASON_EVIDENCE_MISSING:
            return OutcomeState.UNABLE_TO_DETERMINE, REASON_EVIDENCE_MISSING
        if code == REASON_EVAL_ERROR:
            return OutcomeState.UNABLE_TO_DETERMINE, REASON_EVAL_ERROR
        return OutcomeState.UNABLE_TO_DETERMINE, REASON_APPLICABILITY_UNKNOWN

    passes = [o for o in applicable if o.passed is True]
    fails = [o for o in applicable if o.passed is False]
    if fails and passes:
        return OutcomeState.PARTIALLY_MET, REASON_MIXED_OBJECTIVES
    if fails:
        return OutcomeState.NOT_MET, REASON_OBJECTIVES_FAILED
    return OutcomeState.MET, REASON_ALL_MET
