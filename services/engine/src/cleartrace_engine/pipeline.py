from __future__ import annotations

from typing import Any

from cleartrace_engine.certainty import certainty_index_v0
from cleartrace_engine.evaluate import (
    evaluate_applicability,
    evaluate_control,
    objective_from_rule,
)
from cleartrace_engine.framework_studio import control_context_from_pack
from cleartrace_engine.opa_client import engine_bundle_digest, evaluate_pack_control
from cleartrace_engine.types import (
    ControlContext,
    EvaluationError,
    EvaluationInput,
    EvaluationOutput,
    ObjectiveResult,
)


def _objectives_from_opa(raw: list[dict[str, Any]]) -> list[ObjectiveResult]:
    objectives: list[ObjectiveResult] = []
    for item in raw:
        objectives.append(
            objective_from_rule(
                objective_key=str(item.get("key", "objective")),
                critical_gate=bool(item.get("critical_gate", False)),
                passed=item.get("passed"),
                applicable=bool(item.get("applicable", True)),
            )
        )
    return objectives


def _assess_pack_control_payload(
    *,
    pack: dict[str, Any],
    control: dict[str, Any],
    system: dict[str, Any],
    evidence: list[dict[str, Any]],
    pack_slug: str,
    cel_context: dict[str, Any] | None = None,
    extra_opa_input: dict[str, Any] | None = None,
    skip_cel: bool = False,
) -> tuple[EvaluationOutput, ControlContext, EvaluationInput]:
    """CEL applicability → OPA objectives/evidence → five-state reducer."""
    ctx = control_context_from_pack(pack, control)
    digest = engine_bundle_digest()
    cel_input = cel_context if cel_context is not None else system
    evaluation_errors: list[EvaluationError] = []
    if skip_cel:
        applicability_known = True
        applicability: bool | None = True
    else:
        expr = control.get("applicability_expr")
        applicability, applicability_known, evaluation_errors = evaluate_applicability(
            expr, cel_input
        )
        if applicability is False and applicability_known:
            payload = EvaluationInput(
                contract_version="1.0",
                control=ctx,
                system=system,
                evidence=evidence,
                metrics=[],
                applicability_known=True,
                applicability=False,
                objective_results=[],
                evaluation_errors=evaluation_errors,
                evidence_issues=[],
                engine_bundle_digest=digest,
            )
            out = evaluate_control(payload)
            return out, ctx, payload

    evidence_specs = control.get("evidence_specs") or []
    opa_input: dict[str, Any] = {
        "system": system,
        "evidence": evidence,
        "evidence_specs": evidence_specs,
    }
    if extra_opa_input:
        opa_input.update(extra_opa_input)

    opa_out = evaluate_pack_control(
        pack_slug=pack_slug,
        control_key=str(control["control_key"]),
        payload=opa_input,
    )

    if not skip_cel and applicability is not None:
        opa_applicable = opa_out.get("applicability", applicability)
        applicability = bool(applicability and opa_applicable)
    elif opa_out.get("applicability") is not None and skip_cel:
        applicability = bool(opa_out.get("applicability"))
        applicability_known = bool(opa_out.get("applicability_known", True))

    objectives = _objectives_from_opa(list(opa_out.get("objectives", [])))
    evidence_issues = list(opa_out.get("evidence_issues", []))

    payload = EvaluationInput(
        contract_version="1.0",
        control=ctx,
        system=system,
        evidence=evidence,
        metrics=[],
        applicability_known=applicability_known,
        applicability=applicability,
        objective_results=objectives,
        evaluation_errors=evaluation_errors,
        evidence_issues=evidence_issues,
        engine_bundle_digest=digest,
    )
    out = evaluate_control(payload)
    return out, ctx, payload


def assess_pack_control(
    *,
    pack: dict[str, Any],
    control: dict[str, Any],
    system: dict[str, Any],
    evidence: list[dict[str, Any]],
    pack_slug: str,
    cel_context: dict[str, Any] | None = None,
    extra_opa_input: dict[str, Any] | None = None,
    skip_cel: bool = False,
) -> tuple[EvaluationOutput, ControlContext]:
    out, ctx, _payload = _assess_pack_control_payload(
        pack=pack,
        control=control,
        system=system,
        evidence=evidence,
        pack_slug=pack_slug,
        cel_context=cel_context,
        extra_opa_input=extra_opa_input,
        skip_cel=skip_cel,
    )
    return out, ctx


def assess_pack_control_with_index(
    *,
    pack: dict[str, Any],
    control: dict[str, Any],
    system: dict[str, Any],
    evidence: list[dict[str, Any]],
    pack_slug: str,
    cel_context: dict[str, Any] | None = None,
    extra_opa_input: dict[str, Any] | None = None,
    skip_cel: bool = False,
) -> tuple[EvaluationOutput, ControlContext, float]:
    out, ctx, payload = _assess_pack_control_payload(
        pack=pack,
        control=control,
        system=system,
        evidence=evidence,
        pack_slug=pack_slug,
        cel_context=cel_context,
        extra_opa_input=extra_opa_input,
        skip_cel=skip_cel,
    )
    return out, ctx, certainty_index_v0(payload)


def finding_metadata(
    pack: dict[str, Any], control: dict[str, Any], ctx: ControlContext
) -> dict[str, str]:
    return {
        "clause_ref": control["clause_ref"],
        "control_key": control["control_key"],
        "control_version": pack.get("version", "1.0.0"),
        "source_url_en": pack["source_url_en"],
        "source_url_fr": pack["source_url_fr"],
        "requirement_en": ctx.requirement_en,
        "requirement_fr": ctx.requirement_fr,
    }
