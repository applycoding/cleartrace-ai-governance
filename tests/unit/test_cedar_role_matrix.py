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
    ],
)
def test_role_matrix_denied(action: str, roles: list[str]) -> None:
    assert not authorized(action, roles)
