from __future__ import annotations

from cleartrace_core_api.auth.context import AuthContext


def authorize_package_b_route(*, auth: AuthContext, path: str, method: str) -> tuple[bool, str]:
    """Blueprint section 8.2 RBAC for evidence, review and audit routes."""
    roles = auth.roles
    if path.startswith("/api/v1/evidence"):
        if method == "POST":
            allowed = roles & {
                "system_owner",
                "assessor",
                "approver",
                "oversight_reviewer",
                "tenant_admin",
                "auditor",
            }
            return (bool(allowed), "upload_evidence")
        return (bool(roles), "view_evidence")
    if "/findings/" in path and path.endswith("/actions") and method == "POST":
        return ("oversight_reviewer" in roles, "review_finding")
    if path.startswith("/api/v1/audit") and method == "GET":
        return (
            bool(roles & {"auditor", "tenant_admin", "platform_operator"}),
            "read_audit",
        )
    return (True, "unknown")
