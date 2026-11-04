"""OpenAPI schema adjustments for Schemathesis contract alignment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cleartrace_engine.framework_studio import list_packs, load_pack

_NO_NUL_PATTERN = "^[^\u0000]*$"

_PACKS_ROOT = Path(__file__).resolve().parents[4] / "policies" / "packs"


def all_shipped_control_keys() -> list[str]:
    keys: list[str] = []
    for path in list_packs(_PACKS_ROOT):
        pack = load_pack(path)
        if pack.get("slug") == "golden":
            continue
        for control in pack.get("controls", []):
            keys.append(str(control["control_key"]))
    return sorted(set(keys))


def patch_string_schemas(node: object) -> None:
    if isinstance(node, dict):
        if node.get("type") == "string" and "pattern" not in node:
            node["pattern"] = _NO_NUL_PATTERN
        for value in node.values():
            patch_string_schemas(value)
    elif isinstance(node, list):
        for item in node:
            patch_string_schemas(item)


def patch_assessment_control_key(schema: dict[str, Any], control_keys: list[str]) -> None:
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    for body in schemas.values():
        if not isinstance(body, dict):
            continue
        props = body.get("properties", {})
        if "pack_slug" in props and "control_key" in props:
            props["control_key"]["enum"] = control_keys


def patch_framework_assignment(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas["FrameworkAssignmentBySystem"] = {
        "type": "object",
        "required": ["framework_version_id", "ai_system_id"],
        "properties": {
            "framework_version_id": {"$ref": "#/components/schemas/UUID"},
            "ai_system_id": {"$ref": "#/components/schemas/UUID"},
            "criteria_overrides": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    }
    schemas["FrameworkAssignmentByGroup"] = {
        "type": "object",
        "required": ["framework_version_id", "group_id"],
        "properties": {
            "framework_version_id": {"$ref": "#/components/schemas/UUID"},
            "group_id": {"$ref": "#/components/schemas/UUID"},
            "criteria_overrides": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    }
    paths = schema.get("paths", {})
    post = paths.get("/api/v1/frameworks/assignments", {}).get("post", {})
    body = post.get("requestBody", {})
    content = body.get("content", {})
    json_body = content.get("application/json", {})
    json_body["schema"] = {
        "oneOf": [
            {"$ref": "#/components/schemas/FrameworkAssignmentBySystem"},
            {"$ref": "#/components/schemas/FrameworkAssignmentByGroup"},
        ]
    }


def patch_systems_cursor(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    get_op = paths.get("/api/v1/systems", {}).get("get", {})
    params = get_op.get("parameters", [])
    for param in params:
        if param.get("name") == "cursor" and param.get("in") == "query":
            param["schema"] = {
                "type": "string",
                "pattern": "^[A-Za-z0-9_-]+=*$",
                "minLength": 4,
                "maxLength": 24,
            }
            param["description"] = (
                "Opaque pagination cursor previously issued in next_cursor (URL-safe base64)."
            )


def patch_systems_patch_if_match(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    patch_op = paths.get("/api/v1/systems/{system_id}", {}).get("patch", {})
    params = patch_op.setdefault("parameters", [])
    if not any(p.get("name") == "If-Match" for p in params):
        params.append(
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": _NO_NUL_PATTERN, "minLength": 1},
            }
        )


def patch_evidence_upload(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    post = paths.get("/api/v1/evidence", {}).get("post", {})
    content = post.get("requestBody", {}).get("content", {})
    multipart = content.get("multipart/form-data", {})
    form_schema = multipart.get("schema", {})
    form_schema["type"] = "object"
    form_schema["required"] = ["file", "artefact_class"]
    form_schema["additionalProperties"] = False
    props = form_schema.setdefault("properties", {})
    props.setdefault("file", {"type": "string", "format": "binary"})
    props["artefact_class"] = {"type": "string", "pattern": _NO_NUL_PATTERN}


def patch_webhook_url(schema: dict[str, Any]) -> None:
    """Match notifier SSRF guard: https URL with a DNS host label, no credentials."""
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    for name, body in schemas.items():
        if not isinstance(body, dict):
            continue
        url_field = body.get("properties", {}).get("url")
        if url_field is None:
            continue
        if name.endswith("WebhookCreate") or name == "WebhookCreate":
            url_field["pattern"] = (
                r"^https://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
                r"[A-Za-z]{2,63}(:[0-9]{1,5})?(?:/[^\s?#]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?$"
            )


def apply_openapi_patches(schema: dict[str, Any]) -> None:
    patch_string_schemas(schema)
    control_keys = all_shipped_control_keys()
    patch_assessment_control_key(schema, control_keys)
    patch_framework_assignment(schema)
    patch_systems_cursor(schema)
    patch_systems_patch_if_match(schema)
    patch_evidence_upload(schema)
    patch_webhook_url(schema)
