from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cleartrace_contracts.models import OutcomeState

from cleartrace_core_api.interop.oscal_profile import (
    LOSSY_NOTE,
    OSCAL_PROFILE_NS,
    OUTCOME_TO_OSCAL,
    build_finding_props,
)
from cleartrace_core_api.interop.validation import validate_oscal_document, validate_references

CYCLONEDX_SCHEMA = (
    "https://raw.githubusercontent.com/CycloneDX/specification/master/schema/bom-1.6.schema.json"
)


class InteropExportService:
    """Build OSCAL 1.2.3 and CycloneDX 1.6 exports for dossier interchange."""

    def capabilities(self) -> dict[str, Any]:
        return {
            "oscal_version": "1.2.3",
            "cyclonedx_version": "1.6",
            "five_state_profile": {
                "namespace": OSCAL_PROFILE_NS,
                "understood": True,
                "lossy_export_note": LOSSY_NOTE,
            },
            "supported_exports": [
                "catalog",
                "profile",
                "ssp",
                "assessment-results",
                "poam",
                "cyclonedx",
            ],
        }

    def export_oscal(self, export_type: str, dossier: dict[str, Any]) -> bytes:
        export_type = export_type.lower()
        builders = {
            "catalog": self._build_catalog,
            "profile": self._build_profile,
            "ssp": self._build_ssp,
            "assessment-results": self._build_assessment_results,
            "poam": self._build_poam,
        }
        if export_type not in builders:
            raise ValueError(f"unsupported OSCAL export type: {export_type}")
        doc = builders[export_type](dossier)
        if export_type == "assessment-results":
            validate_oscal_document(doc)
            dangling = validate_references(doc)
            if dangling:
                raise ValueError(f"dangling references: {dangling}")
        return json.dumps(doc, indent=2).encode()

    def export_cyclonedx(self, system: dict[str, Any]) -> bytes:
        now = datetime.now(tz=UTC).isoformat()
        component_uuid = str(system.get("id", uuid4()))
        doc: dict[str, Any] = {
            "$schema": CYCLONEDX_SCHEMA,
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": now,
                "component": {
                    "type": "application",
                    "name": system.get("name_en", "ClearTrace system"),
                    "version": system.get("version", "0.1.0"),
                    "bom-ref": component_uuid,
                },
                "properties": [
                    {"name": "cleartrace:system_key", "value": system.get("system_key", "")},
                    {"name": "cleartrace:lossy_export_note", "value": LOSSY_NOTE},
                ],
            },
            "components": [
                {
                    "type": "machine-learning-model",
                    "name": model.get("name", "model"),
                    "version": model.get("version", "1"),
                    "bom-ref": model.get("id", str(uuid4())),
                }
                for model in system.get("models", [])
            ]
            or [
                {
                    "type": "machine-learning-model",
                    "name": "baseline-model",
                    "version": "1",
                    "bom-ref": str(uuid4()),
                }
            ],
        }
        return json.dumps(doc, indent=2).encode()

    def dossier_from_seed(self, *, system_key: str, name_en: str, name_fr: str) -> dict[str, Any]:
        system_id = uuid4()
        findings = []
        for outcome, control_id in (
            (OutcomeState.MET, "control-1"),
            (OutcomeState.PARTIALLY_MET, "control-2"),
            (OutcomeState.NOT_MET, "control-3"),
            (OutcomeState.NOT_APPLICABLE, "control-4"),
            (OutcomeState.UNABLE_TO_DETERMINE, "control-5"),
        ):
            finding_uuid = str(uuid4())
            mapping = OUTCOME_TO_OSCAL[outcome]
            props = build_finding_props(outcome)
            finding: dict[str, Any] = {
                "uuid": finding_uuid,
                "title": f"Finding for {control_id}",
                "description": f"ClearTrace outcome {outcome.value}",
                "target": {
                    "type": "objective-id",
                    "target-id": control_id,
                    "status": {
                        "state": mapping["status_state"],
                        "reason": mapping["reason"],
                    },
                },
            }
            if props:
                finding["props"] = props
            findings.append(finding)
        return {
            "system": {
                "id": str(system_id),
                "system_key": system_key,
                "name_en": name_en,
                "name_fr": name_fr,
                "version": "1.0.0",
                "models": [{"id": str(uuid4()), "name": "primary", "version": "1"}],
            },
            "findings": findings,
            "lossy_note": LOSSY_NOTE,
        }

    def _build_catalog(self, dossier: dict[str, Any]) -> dict[str, Any]:
        cat_uuid = str(uuid4())
        return {
            "catalog": {
                "uuid": cat_uuid,
                "metadata": self._metadata("ClearTrace export catalog"),
                "groups": [{"id": "cleartrace-controls", "title": "ClearTrace controls"}],
            }
        }

    def _build_profile(self, dossier: dict[str, Any]) -> dict[str, Any]:
        return {
            "profile": {
                "uuid": str(uuid4()),
                "metadata": self._metadata("ClearTrace five-state profile"),
                "imports": [{"href": "#catalog"}],
                "props": [
                    {"name": "profile-namespace", "value": OSCAL_PROFILE_NS},
                    {"name": "lossy-for-state-only-consumers", "value": "true"},
                ],
            }
        }

    def _build_ssp(self, dossier: dict[str, Any]) -> dict[str, Any]:
        system = dossier["system"]
        return {
            "system-security-plan": {
                "uuid": str(uuid4()),
                "metadata": self._metadata(system["name_en"]),
                "system-characteristics": {
                    "system-id": {
                        "identifier-type": "cleartrace-system-key",
                        "id": system["system_key"],
                    }
                },
                "control-implementation": {"implemented-requirements": []},
            }
        }

    def _build_assessment_results(self, dossier: dict[str, Any]) -> dict[str, Any]:
        result_uuid = str(uuid4())
        now = datetime.now(tz=UTC).isoformat()
        return {
            "assessment-results": {
                "uuid": result_uuid,
                "metadata": self._metadata("ClearTrace assessment results"),
                "import-ap": {
                    "href": "https://cleartrace.local/assessment-plan/trivision-ap.json",
                },
                "results": [
                    {
                        "uuid": str(uuid4()),
                        "title": "ClearTrace automated assessment",
                        "description": dossier.get("lossy_note", LOSSY_NOTE),
                        "start": now,
                        "reviewed-controls": {
                            "control-selections": [
                                {
                                    "include-controls": [
                                        {"control-id": "ac-1"},
                                        {"control-id": "ac-2"},
                                    ]
                                }
                            ]
                        },
                        "findings": dossier["findings"],
                    }
                ],
            }
        }

    def _build_poam(self, dossier: dict[str, Any]) -> dict[str, Any]:
        return {
            "plan-of-action-and-milestones": {
                "uuid": str(uuid4()),
                "metadata": self._metadata("ClearTrace POA&M"),
                "poam-items": [],
            }
        }

    def _metadata(self, title: str) -> dict[str, Any]:
        return {
            "title": title,
            "last-modified": datetime.now(tz=UTC).isoformat(),
            "version": "0.1.0",
            "oscal-version": "1.2.3",
            "props": [{"name": "generator", "value": "ClearTrace interop exporter"}],
        }

    def outcome_states_preserved(self, document: dict[str, Any]) -> tuple[int, int]:
        results = document.get("assessment-results", {}).get("results", [{}])
        findings = results[0].get("findings", [])
        preserved = 0
        for finding in findings:
            props = finding.get("props") or []
            outcome_prop = next((p for p in props if p.get("name") == "outcome-state"), None)
            status = finding.get("target", {}).get("status", {})
            state = status.get("state")
            reason = status.get("reason")
            if (
                (state == "satisfied" and reason == "pass")
                or outcome_prop is not None
                or (state == "not-satisfied" and reason == "fail")
            ):
                preserved += 1
        return preserved, len(findings)
