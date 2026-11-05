from __future__ import annotations

from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from cleartrace_core_api.openapi_contract import NO_NUL_PATTERN


def _schema() -> dict:
    return create_app(Settings(dev_skip_auth=True, dev_auth_token="contract")).openapi()


def _patterns(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("pattern") == NO_NUL_PATTERN:
            found.append(str(node.get("type")))
        for value in node.values():
            found.extend(_patterns(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_patterns(item))
    return found


def test_problem_detail_keeps_no_nul_pattern_off() -> None:
    # The error body may quote rejected input, so it must not carry the request-side pattern.
    assert _patterns(_schema()["components"]["schemas"]["ProblemDetail"]) == []


def test_request_strings_carry_no_nul_pattern() -> None:
    schema = _schema()
    assert _patterns(schema["components"]["schemas"]["CreateSystemRequest"])
    for operations in schema["paths"].values():
        for op in operations.values():
            if isinstance(op, dict):
                assert _patterns(op.get("responses", {})) == []


def test_evidence_file_upload_allows_binary_nul() -> None:
    """Binary file parts may contain NUL; Schemathesis ST201 flagged a no-NUL pattern here."""
    schema = _schema()
    body = schema["components"]["schemas"]["Body_upload_evidence_api_v1_evidence_post"]
    file_schema = body["properties"]["file"]
    assert file_schema.get("format") == "binary"
    assert "pattern" not in file_schema
    assert body["properties"]["title_en"].get("pattern") == NO_NUL_PATTERN
    assert "enum" in body["properties"]["artefact_class"]
