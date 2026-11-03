from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cleartrace_engine.cel_evaluator import CELEvaluationError, evaluate_cel
from cleartrace_engine.certainty import certainty_index_v0
from cleartrace_engine.explanation import build_explanation
from cleartrace_engine.reducer import reduce_outcome
from cleartrace_engine.types import (
    EvaluationError,
    EvaluationInput,
    EvaluationOutput,
    ObjectiveResult,
)


def bundle_digest(rego_root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(rego_root.rglob("*.rego")):
        hasher.update(str(path.relative_to(rego_root)).encode())
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def check_evidence(evidence: list[dict[str, object]], specs: list[dict[str, object]]) -> list[str]:
    issues: list[str] = []
    if not specs:
        return issues
    for spec in specs:
        required = bool(spec.get("required", True))
        if not required:
            continue
        matching = [e for e in evidence if e.get("type") == spec.get("type")]
        if not matching:
            issues.append("EVIDENCE_MISSING")
            continue
        for item in matching:
            if item.get("authorized_submitter") is False:
                issues.append("SUBMITTER_UNAUTHORIZED")
            valid_until = item.get("valid_until")
            if valid_until == "expired":
                issues.append("EVIDENCE_STALE")
    return issues


def evaluate_control(payload: EvaluationInput) -> EvaluationOutput:
    state, reason = reduce_outcome(
        applicability_known=payload.applicability_known,
        applicability=payload.applicability,
        objective_results=payload.objective_results,
        evaluation_errors=payload.evaluation_errors,
        evidence_issues=payload.evidence_issues,
    )
    score = certainty_index_v0(payload)
    explanation_en, explanation_fr = build_explanation(payload, state.value, reason, score)
    return EvaluationOutput(
        outcome_state=state.value,
        reason_code=reason,
        certainty_index=score,
        explanation_en=explanation_en,
        explanation_fr=explanation_fr,
    )


def evaluate_applicability(
    expression: str | None, context: dict[str, object]
) -> tuple[bool | None, bool, list[EvaluationError]]:
    if not expression:
        return True, True, []
    try:
        result = evaluate_cel(expression, context)
        return result, True, []
    except CELEvaluationError as exc:
        return (
            None,
            False,
            [EvaluationError(code=exc.code, message_en=exc.message_en, message_fr=exc.message_fr)],
        )


def evaluation_to_contract(output: EvaluationOutput, payload: EvaluationInput) -> dict[str, object]:
    return {
        "contract_version": payload.contract_version,
        "control_id": payload.control.control_id,
        "inputs": {
            "system": payload.system,
            "evidence": payload.evidence,
            "metrics": payload.metrics,
        },
        "outputs": {
            "outcome_state": output.outcome_state,
            "reason_code": output.reason_code,
            "certainty_index": output.certainty_index,
        },
        "errors": [
            {"code": e.code, "message_en": e.message_en, "message_fr": e.message_fr}
            for e in payload.evaluation_errors
        ],
        "explanations": {"en": output.explanation_en, "fr": output.explanation_fr},
    }


def objective_from_rule(
    *,
    objective_key: str,
    critical_gate: bool,
    passed: bool | None,
    applicable: bool = True,
) -> ObjectiveResult:
    return ObjectiveResult(
        objective_key=objective_key,
        applicable=applicable,
        passed=passed,
        critical_gate=critical_gate,
    )


def stable_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
