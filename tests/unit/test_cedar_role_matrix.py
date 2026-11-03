from __future__ import annotations

from pathlib import Path

import cedarpy
import pytest

POLICY = Path("policies/cedar/authz.cedar").read_text(encoding="utf-8")


def authorized(action: str, roles: list[str]) -> bool:
    request = {
        "principal": {"type": "ClearTrace::User", "id": "tester"},
        "action": {"type": "Action", "id": action},
        "resource": {"type": "ClearTrace::Api", "id": "/api/v1/systems"},
        "context": {"roles": roles},
    }
    result = cedarpy.is_authorized(request, POLICY, [])
    return result.decision == cedarpy.Decision.Allow


@pytest.mark.parametrize(
    ("action", "roles"),
    [
        ("view_system", ["tenant_admin"]),
        ("view_system", ["read_only_viewer"]),
        ("create_system", ["system_owner"]),
        ("admin", ["tenant_admin"]),
        ("upload_evidence", ["assessor"]),
        ("view_evidence", ["auditor"]),
        ("review_finding", ["oversight_reviewer"]),
        ("read_audit", ["auditor"]),
        ("verify_audit", ["tenant_admin"]),
        ("mutate_data_policy", ["tenant_admin"]),
        ("view_data_policy", ["system_owner"]),
        ("export_interop", ["read_only_viewer"]),
        ("manage_connectors", ["tenant_admin"]),
        ("run_connector", ["system_owner"]),
        ("register_import", ["system_owner"]),
        ("promote_policy_diff", ["policy_steward"]),
        ("post_observations", ["assessor"]),
        ("manage_webhooks", ["tenant_admin"]),
        ("create_report", ["read_only_viewer"]),
        ("aia_score", ["assessor"]),
        ("run_assessment", ["assessor"]),
    ],
)
def test_role_matrix_allowed(action: str, roles: list[str]) -> None:
    assert authorized(action, roles)


@pytest.mark.parametrize(
    ("action", "roles"),
    [
        ("admin", ["system_owner"]),
        ("create_system", ["read_only_viewer"]),
        ("update_system", ["assessor"]),
        ("view_system", ["platform_operator"]),
        ("upload_evidence", ["read_only_viewer"]),
        ("review_finding", ["system_owner"]),
        ("read_audit", ["system_owner"]),
        ("mutate_data_policy", ["system_owner"]),
        ("promote_policy_diff", ["read_only_viewer"]),
        ("post_observations", ["read_only_viewer"]),
        ("manage_webhooks", ["system_owner"]),
        ("run_assessment", ["read_only_viewer"]),
    ],
)
def test_role_matrix_denied(action: str, roles: list[str]) -> None:
    assert not authorized(action, roles)
