"""OpenAPI contract helpers (Schemathesis ST202, api/openapi.yaml parity)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cleartrace_engine.framework_studio import list_packs, load_pack
from cleartrace_evidence.constants import ARTEFACT_CLASSES

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
_RESPONSE_ONLY_COMPONENTS = frozenset({"ProblemDetail", "NoNulJsonValue"})


def _ensure_no_nul_json_value(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components["NoNulJsonValue"] = {
        "anyOf": [
            {"type": "string", "pattern": NO_NUL_PATTERN},
            {"type": "number"},
            {"type": "integer"},
            {"type": "boolean"},
            {"type": "null"},
            {"type": "array", "items": {"$ref": "#/components/schemas/NoNulJsonValue"}},
            {
                "type": "object",
                "propertyNames": {"type": "string", "pattern": NO_NUL_PATTERN},
                "additionalProperties": {"$ref": "#/components/schemas/NoNulJsonValue"},
            },
        ]
    }


def apply_no_nul_string_pattern(schema: dict[str, Any]) -> None:
    """Add a no-NUL pattern to request-side string schemas (Schemathesis ST202).

    Operation responses and response-only components are left unchanged. Free-form
    objects are constrained by ``constrain_freeform_objects`` so NUL cannot appear in
    keys or values while still remaining schema-valid for ordinary JSON.
    """

    def _patch(obj: dict[str, Any]) -> None:
        if obj.get("type") != "string" or "pattern" in obj:
            return
        # Binary uploads may legally contain NUL bytes; do not constrain them.
        if obj.get("format") == "binary":
            return
        media = str(obj.get("contentMediaType", "")).lower()
        if media.startswith("application/octet-stream") or media.startswith("image/"):
            return
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


def constrain_freeform_objects(schema: dict[str, Any]) -> None:
    """Replace boolean additionalProperties:true with a no-NUL JSON value schema."""
    _ensure_no_nul_json_value(schema)

    def _patch(obj: dict[str, Any]) -> None:
        if obj.get("type") != "object":
            return
        additional = obj.get("additionalProperties")
        if additional is True:
            obj["propertyNames"] = {"type": "string", "pattern": NO_NUL_PATTERN}
            obj["additionalProperties"] = {"$ref": "#/components/schemas/NoNulJsonValue"}

    for operations in schema.get("paths", {}).values():
        if not isinstance(operations, dict):
            continue
        for _key, op in operations.items():
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
                param["schema"] = {
                    "type": "string",
                    "pattern": CURSOR_PATTERN,
                    "minLength": 4,
                    "maxLength": 24,
                }
                param["description"] = (
                    "Opaque pagination cursor previously issued in next_cursor (URL-safe base64). "
                    "A pattern-valid cursor this API did not issue yields an empty page."
                )


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
                "schema": {"type": "string", "pattern": NO_NUL_PATTERN, "minLength": 1},
            }
        )
    responses = patch.setdefault("responses", {})
    responses["409"] = {
        "description": "If-Match missing or does not match the current ETag",
        "content": {
            "application/problem+json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}
        },
    }


def annotate_assessment_and_assignment_errors(schema: dict[str, Any]) -> None:
    assessments = schema.get("paths", {}).get("/api/v1/assessments", {}).get("post")
    if isinstance(assessments, dict):
        assessments.setdefault("responses", {})["404"] = {
            "description": "Unknown pack, control key, or AI system",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                }
            },
        }
    assignments = schema.get("paths", {}).get("/api/v1/frameworks/assignments", {}).get("post")
    if isinstance(assignments, dict):
        assignments.setdefault("responses", {})["409"] = {
            "description": "Exactly one of ai_system_id or group_id is required",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                }
            },
        }


def annotate_evidence_multipart(schema: dict[str, Any]) -> None:
    post = schema.get("paths", {}).get("/api/v1/evidence", {}).get("post")
    if not isinstance(post, dict):
        return
    content = post.setdefault("requestBody", {}).setdefault("content", {})
    multipart_wrapper = content.setdefault("multipart/form-data", {})
    multipart = multipart_wrapper.setdefault("schema", {})
    if not isinstance(multipart, dict):
        return
    targets: list[dict[str, Any]] = [multipart]
    ref = multipart.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        component = schema.get("components", {}).get("schemas", {}).get(name)
        if isinstance(component, dict):
            targets.append(component)
    for target in targets:
        props = target.setdefault("properties", {})
        # Binary file bodies may contain NUL; never attach the no-NUL pattern.
        props["file"] = {"type": "string", "contentMediaType": "application/octet-stream"}
        props["artefact_class"] = {
            "type": "string",
            "enum": sorted(ARTEFACT_CLASSES),
            "pattern": NO_NUL_PATTERN,
            "minLength": 1,
        }
        props["title_en"] = {
            "type": "string",
            "pattern": NO_NUL_PATTERN,
            "default": "Evidence artefact",
        }
        props["title_fr"] = {
            "type": "string",
            "pattern": NO_NUL_PATTERN,
            "default": "Artefact de preuve",
        }
        target["additionalProperties"] = False
        required = target.setdefault("required", [])
        for field in ("file", "artefact_class"):
            if field not in required:
                required.append(field)


def _all_control_keys() -> list[str]:
    keys: list[str] = []
    if not _PACKS_ROOT.is_dir():
        return keys
    for path in list_packs(_PACKS_ROOT):
        pack = load_pack(path)
        for control in pack.get("controls", []):
            keys.append(str(control["control_key"]))
    return sorted(set(keys))


def _pack_control_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if not _PACKS_ROOT.is_dir():
        return pairs
    for path in list_packs(_PACKS_ROOT):
        pack = load_pack(path)
        slug = str(pack["slug"])
        for control in pack.get("controls", []):
            pairs.append((slug, str(control["control_key"])))
    return pairs


def annotate_assessment_control_keys(schema: dict[str, Any]) -> None:
    """Limit control_key to keys that exist, and document pack+control pairing via oneOf."""
    pairs = _pack_control_pairs()
    if not pairs:
        return
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    body = components.get("StartAssessmentRequest")
    if not isinstance(body, dict):
        return
    # Keep the closed request shape; Schemathesis still needs a single object schema.
    # Unknown pack/control pairs are answered with 404 by the handler.
    props = body.setdefault("properties", {})
    control = props.setdefault("control_key", {})
    keys = sorted({key for _slug, key in pairs})
    if isinstance(control, dict):
        control.clear()
        control.update({"anyOf": [{"type": "null"}, {"type": "string", "enum": keys}]})
    pack = props.setdefault("pack_slug", {})
    slugs = sorted({slug for slug, _key in pairs})
    if isinstance(pack, dict) and slugs:
        pack["enum"] = slugs


def annotate_assignment_exactly_one(schema: dict[str, Any]) -> None:
    """Document the assignment body as exactly one of the two closed shapes."""
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    if not isinstance(components.get("AssignmentCreate"), dict):
        return
    overrides = {
        "type": "object",
        "propertyNames": {"type": "string", "pattern": NO_NUL_PATTERN},
        "additionalProperties": {"$ref": "#/components/schemas/NoNulJsonValue"},
    }
    uuid = {"type": "string", "format": "uuid"}
    for name, target in (
        ("FrameworkAssignmentBySystem", "ai_system_id"),
        ("FrameworkAssignmentByGroup", "group_id"),
    ):
        components[name] = {
            "type": "object",
            "required": ["framework_version_id", target],
            "properties": {
                "framework_version_id": uuid,
                target: uuid,
                "criteria_overrides": overrides,
            },
            "additionalProperties": False,
        }
    post = schema.get("paths", {}).get("/api/v1/frameworks/assignments", {}).get("post")
    if not isinstance(post, dict):
        return
    body = post.get("requestBody", {}).get("content", {}).get("application/json")
    if isinstance(body, dict):
        body["schema"] = {
            "oneOf": [
                {"$ref": "#/components/schemas/FrameworkAssignmentBySystem"},
                {"$ref": "#/components/schemas/FrameworkAssignmentByGroup"},
            ]
        }


WEBHOOK_URL_PATTERN = (
    r"^https://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}(:(?:6553[0-5]|655[0-2][0-9]|65[0-4][0-9]{2}|6[0-4][0-9]{3}|[1-5][0-9]{4}|[1-9][0-9]{0,3}))?(?:/[^\s?#]*)?(?:\?[^\s#]*)?(?:#[^\s]*)?$"
)


def annotate_webhook_url(schema: dict[str, Any]) -> None:
    """Express the notifier's DNS-host rule (an IP literal is refused) in the schema."""
    components = schema.get("components", {}).get("schemas", {})
    for name, body in components.items():
        if name.endswith("WebhookCreate") and isinstance(body, dict):
            url = body.get("properties", {}).get("url")
            if isinstance(url, dict):
                url["pattern"] = WEBHOOK_URL_PATTERN


def apply_contract_annotations(schema: dict[str, Any]) -> None:
    apply_no_nul_string_pattern(schema)
    constrain_freeform_objects(schema)
    annotate_list_systems_cursor(schema)
    annotate_patch_system_preconditions(schema)
    annotate_assessment_and_assignment_errors(schema)
    annotate_assessment_control_keys(schema)
    annotate_assignment_exactly_one(schema)
    annotate_evidence_multipart(schema)
    annotate_webhook_url(schema)
