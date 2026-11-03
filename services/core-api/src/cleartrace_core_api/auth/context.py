from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    subject: str
    tenant_id: UUID
    roles: frozenset[str]
    org_unit: str | None
    raw_claims: dict[str, Any]
