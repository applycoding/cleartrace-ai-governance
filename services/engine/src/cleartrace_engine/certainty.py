from __future__ import annotations

from cleartrace_engine.types import EvaluationInput


def certainty_index_v0(payload: EvaluationInput) -> float:
    """Blueprint section 6.5 version 0 weighted rule (uncalibrated index)."""
    required = 0
    present = 0
    for obj in payload.objective_results:
        if not obj.applicable:
            continue
        required += 1
        if obj.passed is True:
            present += 1
    completeness = (present / required) if required else 0.0

    freshness = 1.0
    for issue in payload.evidence_issues:
        if issue == "EVIDENCE_STALE":
            freshness = 0.4
            break
        if issue == "EVIDENCE_MISSING":
            freshness = 0.2
            break

    auth = 0.3 if "SUBMITTER_UNAUTHORIZED" in payload.evidence_issues else 1.0
    deterministic = 0.85 if payload.used_llm else 1.0
    error_penalty = 0.0 if payload.evaluation_errors else 1.0

    score = (
        0.35 * completeness
        + 0.25 * freshness
        + 0.20 * auth
        + 0.10 * deterministic
        + 0.10 * error_penalty
    )
    return round(min(1.0, max(0.0, score)), 2)


def certainty_band(score: float) -> tuple[str, str]:
    if score >= 0.80:
        return ("high", "élevé")
    if score >= 0.50:
        return ("medium", "moyen")
    return ("low", "faible")
