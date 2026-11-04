"""OpenAPI contract helpers (Schemathesis ST202, api/openapi.yaml parity)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cleartrace_engine.framework_studio import list_packs, load_pack

_PACKS_ROOT = Path(__file__).resolve().parents[4] / "policies" / "packs"

# PostgreSQL text/jsonb cannot store U+0000; reject at the middleware with 422.
NO_NUL_PATTERN = "^[^\u0000]*$"

# Cursors are url-safe base64 of a decimal offset issued by this API.
CURSOR_PATTERN = "^[A-Za-z0-9_-]+=*$"

# Idempotency-Key: 1–128 visible ASCII, no spaces (matches IdempotencyMiddleware).
IDEMPOTENCY_KEY_PATTERN = "^[!-~]{1,128}$"


def _walk_schemas(node: Any, *, apply: Any) -> None:
    if isinstance(node, dict):
        apply(node)
        for value in node.values():
            _walk_schemas(value, apply=apply)
    elif isinstance(node, list):
        for item in node:
            _walk_schemas(item, apply=apply)


# Response-only schemas. ProblemDetail.detail may quote the rejected input (which can
# hold NUL), so a no-NUL pattern there would make valid error responses fail the schema.
_RESPONSE_ONLY_COMPONENTS = frozenset({"ProblemDetail"})


def apply_no_nul_string_pattern(schema: dict[str, Any]) -> None:
    """Add a no-NUL pattern to request-side string schemas (Schemathesis ST202).

    Operation responses and response-only components are left unchanged. Free-form
    objects (additionalProperties) can still carry NUL in keys or values, which the
    JSON input guard rejects with 422; a string pattern cannot express that.
    """

    def _patch(obj: dict[str, Any]) -> None:
        if obj.get("type") == "string" and "pattern" not in obj:
            obj["pattern"] = NO_NUL_PATTERN

    for operations in schema.get("paths", {}).values():
        if not isinstance(operations, dict):
            continue
        for key, op in operations.items():
            if key == "parameters":
                _walk_schemas(op, apply=_patch)
                continue
            if not isinstance(op, dict):
                continue
            for section, value in op.items():
                if section != "responses":
                    _walk_schemas(value, apply=_patch)
    components = schema.get("components", {}).get("schemas", {})
    for name, component in components.items():
        if name not in _RESPONSE_ONLY_COMPONENTS:
            _walk_schemas(component, apply=_patch)


def annotate_list_systems_cursor(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    systems = paths.get("/api/v1/systems", {})
    get_op = systems.get("get")
    if not isinstance(get_op, dict):
        return
    params = get_op.setdefault("parameters", [])
    for param in params:
        if isinstance(param, dict) and param.get("name") == "cursor" and param.get("in") == "query":
            param.setdefault("schema", {})
            if isinstance(param["schema"], dict):
                param["schema"]["type"] = "string"
                param["schema"]["pattern"] = CURSOR_PATTERN
    get_op.setdefault("responses", {})["400"] = {
        "description": "Invalid pagination cursor",
        "content": {
            "application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}
        },
    }


def annotate_patch_system_preconditions(schema: dict[str, Any]) -> None:
    paths = schema.get("paths", {})
    item = paths.get("/api/v1/systems/{system_id}", {})
    patch = item.get("patch")
    if not isinstance(patch, dict):
        return
    params = patch.setdefault("parameters", [])
    if not any(p.get("name") == "If-Match" for p in params if isinstance(p, dict)):
        params.append(
            {
                "name": "If-Match",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": NO_NUL_PATTERN},
            }
        )
    responses = patch.setdefault("responses", {})
    for code, description in (
        ("428", "If-Match header required"),
        ("412", "If-Match precondition failed"),
    ):
        responses.setdefault(
            code,
            {
                "description": description,
                "content": {
                    "application/problem+json": {
                        "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                    }
                },
            },
        )


def annotate_assessment_and_assignment_errors(schema: dict[str, Any]) -> None:
    assessments = schema.get("paths", {}).get("/api/v1/assessments", {}).get("post")
    if isinstance(assessments, dict):
        assessments.setdefault("responses", {})["400"] = {
            "description": "Unknown pack or control key",
            "content": {
                "application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}
            },
        }
    assignments = schema.get("paths", {}).get("/api/v1/frameworks/assignments", {}).get("post")
    if isinstance(assignments, dict):
        assignments.setdefault("responses", {})["400"] = {
            "description": "Exactly one of ai_system_id or group_id is required",
            "content": {
                "application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}
            },
        }


def annotate_evidence_multipart(schema: dict[str, Any]) -> None:
    post = schema.get("paths", {}).get("/api/v1/evidence", {}).get("post")
    if not isinstance(post, dict):
        return
    content = post.setdefault("requestBody", {}).setdefault("content", {})
    multipart = content.setdefault("multipart/form-data", {}).setdefault("schema", {})
    if not isinstance(multipart, dict):
        return
    props = multipart.setdefault("properties", {})
    props.setdefault(
        "artefact_class",
        {"type": "string", "pattern": NO_NUL_PATTERN, "minLength": 1},
    )
    required = multipart.setdefault("required", [])
    if "artefact_class" not in required:
        required.append("artefact_class")


def _all_control_keys() -> list[str]:
    keys: list[str] = []
    if not _PACKS_ROOT.is_dir():
        return keys
    for path in list_packs(_PACKS_ROOT):
        pack = load_pack(path)
        for control in pack.get("controls", []):
            keys.append(str(control["control_key"]))
    return sorted(set(keys))


def annotate_assessment_control_keys(schema: dict[str, Any]) -> None:
    keys = _all_control_keys()
    if not keys:
        return
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    body = components.get("StartAssessmentRequest")
    if not isinstance(body, dict):
        return
    props = body.setdefault("properties", {})
    control = props.setdefault("control_key", {})
    if isinstance(control, dict):
        control["anyOf"] = [{"type": "null"}, {"type": "string", "enum": keys}]


def annotate_assignment_exactly_one(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    body = components.get("AssignmentCreate")
    if not isinstance(body, dict):
        return
    body["oneOf"] = [
        {"required": ["framework_version_id", "ai_system_id"]},
        {"required": ["framework_version_id", "group_id"]},
    ]


def apply_contract_annotations(schema: dict[str, Any]) -> None:
    apply_no_nul_string_pattern(schema)
    annotate_list_systems_cursor(schema)
    annotate_patch_system_preconditions(schema)
    annotate_assessment_and_assignment_errors(schema)
    annotate_assessment_control_keys(schema)
    annotate_assignment_exactly_one(schema)
    annotate_evidence_multipart(schema)
