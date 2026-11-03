from __future__ import annotations

from typing import Any

from trestle.oscal.assessment_results import Model as AssessmentResultsModel


def validate_oscal_document(document: dict[str, Any]) -> None:
    """Validate against OSCAL 1.2.3 using compliance-trestle (external test tool)."""
    AssessmentResultsModel.model_validate(document)


def validate_references(document: dict[str, Any]) -> list[str]:
    """Return dangling UUID references (empty list means OK)."""
    known: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"uuid", "component-uuid", "party-uuid"} and isinstance(value, str):
                    known.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    dangling: list[str] = []
    refs: set[str] = set()

    def collect_refs(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("-uuid") and isinstance(value, str):
                    refs.add(value)
                collect_refs(value)
        elif isinstance(node, list):
            for item in node:
                collect_refs(item)

    collect_refs(document)
    for ref in refs:
        if ref and ref not in known and len(ref) == 36:
            dangling.append(ref)
    return dangling
