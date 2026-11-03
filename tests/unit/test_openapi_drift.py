from __future__ import annotations

from pathlib import Path

import yaml
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "api" / "openapi.yaml"

PUBLIC_PATHS = {
    ("/health", "get"),
    ("/capabilities", "get"),
}


def _app_routes() -> set[tuple[str, str]]:
    app = create_app(Settings(dev_skip_auth=True, dev_auth_token="openapi-drift"))
    schema = app.openapi()
    routes: set[tuple[str, str]] = set()
    for path, operations in schema.get("paths", {}).items():
        if not path.startswith("/api/v1"):
            continue
        rel = path.removeprefix("/api/v1") or "/"
        for method in operations:
            if method.startswith("x-"):
                continue
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            routes.add((rel, method.lower()))
    routes -= PUBLIC_PATHS
    return routes


def _spec_routes() -> set[tuple[str, str]]:
    spec = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    result: set[tuple[str, str]] = set()
    for path, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method, op in operations.items():
            if method.startswith("x-"):
                continue
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            security = op.get("security") if isinstance(op, dict) else None
            if security == []:
                continue
            result.add((path, method.lower()))
    return result


def _normalize_path(path: str) -> str:
    """Map OpenAPI path params to FastAPI names for comparison."""
    return (
        path.replace("{system_id}", "{system_id}")
        .replace("{finding_id}", "{finding_id}")
        .replace("{job_id}", "{job_id}")
        .replace("{connector_id}", "{connector_id}")
        .replace("{diff_id}", "{diff_id}")
        .replace("{impact_id}", "{impact_id}")
        .replace("{metric_id}", "{metric_id}")
        .replace("{report_id}", "{report_id}")
        .replace("{record_id}", "{record_id}")
        .replace("{export_type}", "{export_type}")
        .replace("{slug}", "{slug}")
        .replace("{certificate_id}", "{certificate_id}")
    )


def test_openapi_matches_fastapi_routes() -> None:
    app_routes = {_normalize_path(p): m for p, m in _app_routes()}
    spec_routes = {_normalize_path(p): m for p, m in _spec_routes()}
    app_set = set(app_routes.items())
    spec_set = set(spec_routes.items())
    missing_in_spec = sorted(app_set - spec_set)
    extra_in_spec = sorted(spec_set - app_set)
    assert not missing_in_spec, f"OpenAPI missing routes: {missing_in_spec}"
    assert not extra_in_spec, f"OpenAPI has extra routes: {extra_in_spec}"
