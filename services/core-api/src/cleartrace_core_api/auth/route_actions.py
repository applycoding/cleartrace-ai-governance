from __future__ import annotations

from fastapi import Request


def action_for_request(request: Request) -> str:
    path = request.url.path
    method = request.method.upper()

    if path == "/api/v1/health":
        return "health"
    if path == "/api/v1/capabilities":
        return "view_dashboard"
    if path.startswith("/api/v1/admin"):
        return "admin"

    if path.startswith("/api/v1/systems"):
        if method == "GET":
            return "view_system"
        if method == "POST":
            return "create_system"
        if method in {"PATCH", "PUT"}:
            return "update_system"

    if path.startswith("/api/v1/assessments"):
        return "run_assessment"

    if path.startswith("/api/v1/evidence"):
        if method == "POST":
            return "upload_evidence"
        return "view_evidence"

    if "/findings/" in path and path.endswith("/actions") and method == "POST":
        return "review_finding"

    if path.startswith("/api/v1/audit"):
        if path.endswith(":verify") or path.endswith("/verify"):
            return "verify_audit"
        return "read_audit"

    if path.startswith("/api/v1/data-policy"):
        if method in {"PUT", "POST"}:
            return "mutate_data_policy"
        return "view_data_policy"

    if path.startswith("/api/v1/export/"):
        return "export_interop"

    if path.startswith("/api/v1/connectors"):
        if ":run" in path or path.endswith("/run"):
            return "run_connector"
        return "manage_connectors"

    if path.startswith("/api/v1/register/"):
        if method == "POST":
            return "register_import"
        return "view_system"

    if path.startswith("/api/v1/policy-"):
        if ":promote" in path and method == "POST":
            return "promote_policy_diff"
        return "view_policy_watch"

    if path.startswith("/api/v1/metrics") or path.startswith("/api/v1/baselines"):
        if method == "POST":
            return "manage_risk_metrics"
        return "view_system"

    if path == "/api/v1/observations" and method == "POST":
        return "post_observations"

    if path.startswith("/api/v1/risks") or path.startswith("/api/v1/data-quality-issues"):
        return "view_system"

    if path.startswith("/api/v1/notifications"):
        return "view_notifications"

    if path == "/api/v1/webhooks" and method == "POST":
        return "manage_webhooks"

    if path.startswith("/api/v1/reports"):
        if method == "POST":
            return "create_report"
        return "view_system"

    if path.startswith("/api/v1/aia"):
        return "aia_score"

    if path.startswith("/api/v1/frameworks"):
        if method == "POST":
            return "admin"
        return "view_system"

    if path.startswith("/api/v1/findings") and method == "GET":
        return "view_system"

    return "view_dashboard"
