from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cedarpy


class CedarAuthorizer:
    """Evaluate Cedar policies for API actions."""

    def __init__(self, policy_path: str | Path) -> None:
        self._policy_path = Path(policy_path)
        self._policy_text = self._policy_path.read_text(encoding="utf-8")

    def is_authorized(
        self,
        *,
        principal: dict[str, Any],
        action: str,
        resource: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> bool:
        request = {
            "principal": principal,
            "action": {"type": "Action", "id": action},
            "resource": resource,
            "context": context or {},
        }
        result = cedarpy.is_authorized(request, self._policy_text, [])
        return result.decision == cedarpy.Decision.Allow

    def reload(self) -> None:
        self._policy_text = self._policy_path.read_text(encoding="utf-8")


def principal_entity(
    subject: str,
    tenant_id: str,
    roles: list[str],
    org_unit: str | None,
) -> dict[str, Any]:
    return {
        "type": "ClearTrace::User",
        "id": subject,
        "attrs": {
            "tenant_id": tenant_id,
            "roles": roles,
            "org_unit": org_unit or "",
        },
    }


def resource_entity(resource_type: str, resource_id: str, tenant_id: str) -> dict[str, Any]:
    return {
        "type": f"ClearTrace::{resource_type}",
        "id": resource_id,
        "attrs": {"tenant_id": tenant_id},
    }


def dump_context(ctx: dict[str, Any]) -> str:
    return json.dumps(ctx, sort_keys=True)
