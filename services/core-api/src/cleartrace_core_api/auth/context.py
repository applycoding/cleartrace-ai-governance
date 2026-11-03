from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5


@dataclass(frozen=True)
class AuthContext:
    subject: str
    tenant_id: UUID
    roles: frozenset[str]
    org_unit: str | None
    raw_claims: dict[str, Any]

    @property
    def actor_id(self) -> UUID:
        """Stable UUID for the caller, used as the audit and reviewer actor.

        Prefer an explicit ``principal_id`` claim, then a UUID-shaped ``sub``.
        OIDC subjects are opaque strings, so any other subject maps to a
        deterministic UUIDv5 scoped by issuer and tenant instead of failing.
        """
        for raw in (self.raw_claims.get("principal_id"), self.subject):
            if raw:
                try:
                    return UUID(str(raw))
                except ValueError:
                    continue
        issuer = str(self.raw_claims.get("iss", ""))
        return uuid5(NAMESPACE_URL, f"cleartrace:{self.tenant_id}:{issuer}:{self.subject}")
