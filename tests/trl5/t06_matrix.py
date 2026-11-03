"""T-06 authorization matrix: 600 allowed + 600 forbidden HTTP requests.

The expected decision for every (role, action) pair is written out by hand in
``EXPECTED_ALLOWED`` and cross-checked against the shipped Cedar policy, so a change
to either side fails the test. Every request template below is a real API route that
returns a 2xx response when the role is allowed, so "allowed" means the request
succeeded, not merely that it was not refused with 403.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

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

# Hand-written role matrix (blueprint section 8 roles). Kept independent of the
# Cedar file on purpose; test_t06_expected_matrix_matches_cedar compares the two.
EXPECTED_ALLOWED: dict[str, frozenset[str]] = {
    "tenant_admin": frozenset(
        {
            "view_dashboard",
            "view_system",
            "create_system",
            "run_assessment",
            "read_audit",
            "verify_audit",
            "view_data_policy",
            "export_interop",
            "manage_connectors",
            "view_policy_watch",
            "view_notifications",
            "create_report",
            "admin",
        }
    ),
    "system_owner": frozenset(
        {
            "view_dashboard",
            "view_system",
            "create_system",
            "view_data_policy",
            "export_interop",
            "manage_connectors",
            "view_notifications",
            "create_report",
        }
    ),
    "assessor": frozenset(
        {"view_dashboard", "view_system", "run_assessment", "export_interop", "create_report"}
    ),
    "read_only_viewer": frozenset(
        {
            "view_dashboard",
            "view_system",
            "view_data_policy",
            "export_interop",
            "view_policy_watch",
            "view_notifications",
            "create_report",
        }
    ),
    "auditor": frozenset(
        {
            "view_dashboard",
            "view_system",
            "read_audit",
            "verify_audit",
            "view_data_policy",
            "export_interop",
            "create_report",
        }
    ),
    "oversight_reviewer": frozenset(
        {"view_dashboard", "view_system", "export_interop", "create_report"}
    ),
}

# Reads that blueprint section 8 calls privileged (admin, support, export) plus the
# audit-log read; each one must leave an audit event with this action.
PRIVILEGED_READ_AUDIT_ACTION: dict[str, str] = {
    "read_audit": "audit.read",
    "admin": "admin.read",
    "export_interop": "export.read",
}


def _no_body(_unique: str, _system_id: UUID) -> dict[str, object] | None:
    return None


@dataclass(frozen=True)
class Template:
    action: str
    method: str
    path: Callable[[UUID], str]
    body: Callable[[str, UUID], dict[str, object] | None] = _no_body
    idempotent_post: bool = False


TEMPLATES: tuple[Template, ...] = (
    Template("view_dashboard", "GET", lambda _s: "/api/v1/capabilities"),
    Template("view_system", "GET", lambda _s: "/api/v1/systems?limit=50"),
    Template("view_system", "GET", lambda s: f"/api/v1/systems/{s}"),
    Template("view_system", "GET", lambda _s: "/api/v1/frameworks"),
    Template(
        "create_system",
        "POST",
        lambda _s: "/api/v1/systems",
        lambda u, _s: {"system_key": f"t06-{u}", "name_en": "T-06 system", "name_fr": "Système T-06"},
        idempotent_post=True,
    ),
    Template(
        "run_assessment",
        "POST",
        lambda _s: "/api/v1/assessments",
        lambda _u, s: {
            "ai_system_id": str(s),
            "pack_slug": "dadm",
            "control_key": "CA-DADM-6-1-1",
            "system_profile": {"planned_production_use": True},
        },
    ),
    Template("read_audit", "GET", lambda _s: "/api/v1/audit/events?limit=5"),
    Template("verify_audit", "POST", lambda _s: "/api/v1/audit:verify"),
    Template("view_data_policy", "GET", lambda _s: "/api/v1/data-policy"),
    Template("export_interop", "GET", lambda _s: "/api/v1/export/oscal/assessment-results"),
    Template("export_interop", "GET", lambda s: f"/api/v1/export/cyclonedx/{s}"),
    Template("manage_connectors", "GET", lambda _s: "/api/v1/connectors"),
    Template("view_policy_watch", "GET", lambda _s: "/api/v1/policy-diffs"),
    Template("view_notifications", "GET", lambda _s: "/api/v1/notifications"),
    Template(
        "create_report",
        "POST",
        lambda _s: "/api/v1/reports",
        lambda _u, _s: {"type": "system_dossier", "language": "en-CA"},
    ),
    Template("admin", "GET", lambda _s: "/api/v1/admin/ping"),
)

ACTIONS = tuple(sorted({t.action for t in TEMPLATES}))


@dataclass(frozen=True)
class Probe:
    tenant_id: UUID
    role: str
    template: Template
    expect_allow: bool


def cedar_allows(action: str, role: str) -> bool:
    request = {
        "principal": {"type": "ClearTrace::User", "id": "matrix"},
        "action": {"type": "Action", "id": action},
        "resource": {"type": "ClearTrace::Api", "id": "/api/v1"},
        "context": {"roles": [role]},
    }
    return cedarpy.is_authorized(request, POLICY, []).decision == cedarpy.Decision.Allow


def base_probes() -> tuple[list[Probe], list[Probe]]:
    """One probe per (tenant, role, template), split by the hand-written matrix."""
    allowed: list[Probe] = []
    denied: list[Probe] = []
    for tenant_id in TENANTS:
        for role in ROLES:
            for template in TEMPLATES:
                expect = template.action in EXPECTED_ALLOWED[role]
                probe = Probe(tenant_id, role, template, expect)
                (allowed if expect else denied).append(probe)
    return allowed, denied


def build_matrix(target_each: int = 600) -> tuple[list[Probe], list[Probe]]:
    """Cycle the base probes until each side has exactly ``target_each`` requests."""
    allowed, denied = base_probes()
    return _cycle(allowed, target_each), _cycle(denied, target_each)


def _cycle(probes: list[Probe], target: int) -> list[Probe]:
    if not probes:
        raise ValueError("empty probe list")
    return [probes[i % len(probes)] for i in range(target)]
