"""Build the T-06 authorization matrix (600 allowed + 600 forbidden HTTP probes)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import cedarpy

POLICY = Path("policies/cedar/authz.cedar").read_text(encoding="utf-8")

TENANTS = (
    UUID("11111111-1111-7111-8111-111111111101"),
    UUID("11111111-1111-7111-8111-111111111102"),
    UUID("11111111-1111-7111-8111-111111111103"),
)

ROLES = (
    "tenant_admin",
    "system_owner",
    "assessor",
    "read_only_viewer",
    "auditor",
    "oversight_reviewer",
)

ACTIONS = (
    "view_dashboard",
    "view_system",
    "create_system",
    "update_system",
    "run_assessment",
    "upload_evidence",
    "view_evidence",
    "review_finding",
    "read_audit",
    "verify_audit",
    "view_data_policy",
    "mutate_data_policy",
    "export_interop",
    "manage_connectors",
    "run_connector",
    "register_import",
    "view_policy_watch",
    "promote_policy_diff",
    "manage_risk_metrics",
    "post_observations",
    "view_notifications",
    "manage_webhooks",
    "create_report",
    "aia_score",
    "admin",
)


@dataclass(frozen=True)
class HttpProbe:
    tenant_id: UUID
    role: str
    method: str
    path: str
    headers: dict[str, str]
    json_body: dict[str, object] | None
    expect_allow: bool
    action: str


def cedar_allows(action: str, role: str) -> bool:
    request = {
        "principal": {"type": "ClearTrace::User", "id": "matrix"},
        "action": {"type": "Action", "id": action},
        "resource": {"type": "ClearTrace::Api", "id": "/api/v1/systems"},
        "context": {"roles": [role]},
    }
    return cedarpy.is_authorized(request, POLICY, []).decision == cedarpy.Decision.Allow


def _paths_for_action(action: str) -> list[tuple[str, str, dict[str, object] | None]]:
    sid = str(uuid4())
    base: dict[str, list[tuple[str, str, dict[str, object] | None]]] = {
        "view_dashboard": [("GET", "/api/v1/capabilities", None)],
        "view_system": [
            ("GET", "/api/v1/systems", None),
            ("GET", "/api/v1/frameworks", None),
            ("GET", f"/api/v1/systems/{sid}/findings", None),
        ],
        "create_system": [
            (
                "POST",
                "/api/v1/systems",
                {"system_key": "t06-key", "name_en": "T06", "name_fr": "T06"},
            ),
        ],
        "update_system": [
            (
                "PATCH",
                f"/api/v1/systems/{sid}",
                {"system_key": "t06-key", "name_en": "T06", "name_fr": "T06"},
            ),
        ],
        "run_assessment": [
            (
                "POST",
                "/api/v1/assessments",
                {
                    "ai_system_id": str(uuid4()),
                    "pack_slug": "dadm",
                    "system_profile": {"planned_production_use": True},
                },
            ),
        ],
        "upload_evidence": [("POST", "/api/v1/evidence", None)],
        "view_evidence": [("GET", "/api/v1/evidence", None)],
        "review_finding": [
            ("POST", f"/api/v1/findings/{uuid4()}/actions", {"action": "approve"}),
        ],
        "read_audit": [("GET", "/api/v1/audit/events", None)],
        "verify_audit": [("POST", "/api/v1/audit/events:verify", None)],
        "view_data_policy": [("GET", "/api/v1/data-policy/retention", None)],
        "mutate_data_policy": [
            (
                "PUT",
                "/api/v1/data-policy/retention",
                {"rules": [], "reason_en": "t06", "reason_fr": "t06"},
            ),
        ],
        "export_interop": [("GET", "/api/v1/export/oscal/assessment-results", None)],
        "manage_connectors": [("GET", "/api/v1/connectors", None)],
        "run_connector": [("POST", f"/api/v1/connectors/{uuid4()}:run", None)],
        "register_import": [("POST", "/api/v1/register/import/gc-ai-register", None)],
        "view_policy_watch": [("GET", "/api/v1/policy-watch/diffs", None)],
        "promote_policy_diff": [
            ("POST", f"/api/v1/policy-watch/diffs/{uuid4()}:promote", None),
        ],
        "manage_risk_metrics": [("POST", "/api/v1/baselines", {"name": "t06"})],
        "post_observations": [
            ("POST", "/api/v1/observations", {"observations": []}),
        ],
        "view_notifications": [("GET", "/api/v1/notifications", None)],
        "manage_webhooks": [
            (
                "POST",
                "/api/v1/webhooks",
                {"url": "https://hooks.example.com/cleartrace", "events": ["alert"]},
            ),
        ],
        "create_report": [
            ("POST", "/api/v1/reports", {"template": "summary", "format": "pdf"}),
        ],
        "aia_score": [
            (
                "POST",
                f"/api/v1/systems/{sid}/aia",
                {"responses": {}, "department_code": "AAA"},
            ),
        ],
        "admin": [("GET", "/api/v1/admin/ping", None)],
    }
    return base.get(action, [("GET", "/api/v1/capabilities", None)])


def build_matrix(*, target_each: int = 600) -> tuple[list[HttpProbe], list[HttpProbe]]:
    allowed: list[HttpProbe] = []
    denied: list[HttpProbe] = []
    for tenant_id in TENANTS:
        for role in ROLES:
            for action in ACTIONS:
                expect = cedar_allows(action, role)
                paths = _paths_for_action(action)
                for variant, (method, path, body) in enumerate(paths):
                    headers: dict[str, str] = {}
                    if method == "POST" and path == "/api/v1/systems":
                        headers["Idempotency-Key"] = f"t06-{tenant_id}-{role}-{action}-{variant}"
                    if method == "PATCH":
                        headers["If-Match"] = 'W/"placeholder"'
                    probe = HttpProbe(
                        tenant_id=tenant_id,
                        role=role,
                        method=method,
                        path=path,
                        headers=headers,
                        json_body=body,
                        expect_allow=expect,
                        action=action,
                    )
                    if expect:
                        allowed.append(probe)
                    else:
                        denied.append(probe)
    allowed = _expand_to(allowed, target_each)
    denied = _expand_to(denied, target_each)
    return allowed, denied


def _expand_to(probes: list[HttpProbe], target: int) -> list[HttpProbe]:
    if not probes:
        raise ValueError("empty probe list")
    out = list(probes)
    idx = 0
    while len(out) < target:
        base = probes[idx % len(probes)]
        dup_headers = dict(base.headers)
        if "Idempotency-Key" in dup_headers:
            dup_headers["Idempotency-Key"] = f"{dup_headers['Idempotency-Key']}-dup{len(out)}"
        out.append(
            HttpProbe(
                tenant_id=base.tenant_id,
                role=base.role,
                method=base.method,
                path=base.path,
                headers=dup_headers,
                json_body=base.json_body,
                expect_allow=base.expect_allow,
                action=base.action,
            )
        )
        idx += 1
    return out[:target]
