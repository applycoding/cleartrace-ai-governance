from __future__ import annotations

from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from cleartrace_risk.breach import BreachProcessor, ControlOutcomeStore, RiskRegister
from cleartrace_risk.catalogue import catalogue_by_code
from cleartrace_risk.thresholds import build_observation
from cleartrace_risk.types import MetricArea, RiskCategory, ThresholdSpec
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from uuid6 import uuid7

router = APIRouter(tags=["risk"])

_catalogue = catalogue_by_code()
_controls = ControlOutcomeStore()
_register = RiskRegister()
_processor = BreachProcessor(controls=_controls, register=_register)


class MetricSummary(BaseModel):
    code: str
    name_en: str
    area: str


class ObservationItem(BaseModel):
    metric_code: str
    ai_system_id: UUID
    value: float = Field(strict=True)
    binding: bool = Field(default=False, strict=True)
    linked_control_id: UUID | None = None


class ObservationBatch(BaseModel):
    observations: list[ObservationItem] = Field(min_length=1)


def _risk_category(spec_area: MetricArea) -> RiskCategory:
    if spec_area in {MetricArea.MODEL_PERFORMANCE, MetricArea.CALIBRATION, MetricArea.FAIRNESS}:
        return RiskCategory.MODEL
    if spec_area in {
        MetricArea.OUTPUT_QUALITY,
        MetricArea.CONSISTENCY,
        MetricArea.SAFETY,
        MetricArea.PERSONAL_INFO,
    }:
        return RiskCategory.OUTPUT
    return RiskCategory.DATA


def _ensure_metric_version(
    cur: Any,
    *,
    tenant_id: UUID,
    metric_code: str,
    spec_name_en: str,
    spec_name_fr: str,
    library: str,
) -> UUID:
    cur.execute(
        """
        SELECT mv.id FROM metric_version mv
        JOIN metric_definition md ON md.id = mv.metric_definition_id
        WHERE md.tenant_id = %s AND md.code = %s
        ORDER BY mv.version_number DESC
        LIMIT 1
        """,
        (tenant_id, metric_code),
    )
    row = cur.fetchone()
    if row:
        return UUID(str(row[0]))
    definition_id = uuid7()
    version_id = uuid7()
    cur.execute(
        """
        INSERT INTO metric_definition (
          id, tenant_id, code, area, name_en, name_fr, library
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (definition_id, tenant_id, metric_code, "data", spec_name_en, spec_name_fr, library),
    )
    cur.execute(
        """
        INSERT INTO metric_version (
          id, tenant_id, metric_definition_id, version_number,
          unit, window_kind, aggregation
        ) VALUES (%s, %s, %s, 1, 'ratio', 'rolling', 'mean')
        """,
        (version_id, tenant_id, definition_id),
    )
    return version_id


@router.get("/metrics")
async def list_metrics() -> dict[str, list[MetricSummary]]:
    items = [
        MetricSummary(code=code, name_en=spec.name_en, area=spec.area.value)
        for code, spec in _catalogue.items()
    ]
    return {"items": items}


@router.post("/metrics", status_code=201)
async def create_metric_definition(request: Request) -> dict[str, str]:
    _ = request
    return {"id": str(uuid7()), "status": "accepted"}


@router.post("/metrics/{metric_id}/versions", status_code=201)
async def create_metric_version(metric_id: UUID, request: Request) -> dict[str, str]:
    _ = request
    return {"metric_id": str(metric_id), "version_id": str(uuid7())}


@router.get("/baselines")
async def list_baselines() -> dict[str, list[dict[str, str]]]:
    return {"items": []}


@router.post("/baselines", status_code=201)
async def create_baseline(request: Request) -> dict[str, str]:
    _ = request
    return {"id": str(uuid7())}


@router.post("/observations", status_code=201)
async def post_observations(request: Request, body: ObservationBatch) -> dict[str, Any]:
    auth = request.state.auth
    settings = request.app.state.settings
    results: list[dict[str, Any]] = []
    for item in body.observations:
        spec = _catalogue.get(item.metric_code)
        if spec is None:
            continue
        category = _risk_category(spec.area)
        control_id = item.linked_control_id or uuid7()
        threshold = ThresholdSpec(
            metric_code=item.metric_code,
            warn_value=spec.default_warn,
            breach_value=spec.default_breach,
            higher_is_worse=spec.higher_is_worse,
            binding=item.binding,
            linked_control_id=control_id,
            name_en=spec.name_en,
            name_fr=spec.name_fr,
        )
        observation = build_observation(
            item.metric_code,
            item.value,
            warn_value=threshold.warn_value,
            breach_value=threshold.breach_value,
            higher_is_worse=threshold.higher_is_worse,
        )
        outcome = _processor.apply(
            system_id=item.ai_system_id,
            threshold=threshold,
            observation=observation,
            category=category,
        )
        observation_id = uuid7()
        with tenant_transaction(settings.database_url, auth.tenant_id) as conn, conn.cursor() as cur:
            version_id = _ensure_metric_version(
                cur,
                tenant_id=auth.tenant_id,
                metric_code=item.metric_code,
                spec_name_en=spec.name_en,
                spec_name_fr=spec.name_fr,
                library=spec.library,
            )
            cur.execute(
                """
                INSERT INTO metric_observation (
                  id, tenant_id, ai_system_id, metric_version_id,
                  window_start, window_end, value, status, details
                ) VALUES (
                  %s, %s, %s, %s, now() - interval '1 hour', now(), %s, %s, %s::jsonb
                )
                """,
                (
                    observation_id,
                    auth.tenant_id,
                    item.ai_system_id,
                    version_id,
                    item.value,
                    observation.status.value,
                    '{"source": "api"}',
                ),
            )
            if outcome.alert_raised:
                cur.execute(
                    """
                    INSERT INTO monitoring_alert (
                      id, tenant_id, ai_system_id, observation_id,
                      severity, binding, message_en, message_fr
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid7(),
                        auth.tenant_id,
                        item.ai_system_id,
                        observation_id,
                        "high" if item.binding else "medium",
                        item.binding,
                        f"Threshold breach on {item.metric_code}",
                        f"Dépassement de seuil pour {item.metric_code}",
                    ),
                )
        results.append(
            {
                "metric_code": item.metric_code,
                "alert_raised": outcome.alert_raised,
                "binding": item.binding,
                "control_outcome_changed": outcome.control_outcome_changed,
            }
        )
    return {"results": results}


@router.get("/risks")
async def list_risks() -> dict[str, list[dict[str, str]]]:
    items = [
        {
            "id": str(entry.get("id", "")),
            "system_id": str(entry.get("system_id", "")),
            "binding": str(entry.get("binding", "")),
        }
        for entry in _register.alerts
    ]
    return {"items": items}


@router.get("/data-quality-issues")
async def list_data_quality_issues() -> dict[str, list[dict[str, str]]]:
    return {"items": []}
