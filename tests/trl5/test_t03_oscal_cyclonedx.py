from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleartrace_contracts.models import OutcomeState
from cleartrace_core_api.interop.exporter import InteropExportService
from cleartrace_core_api.interop.oscal_profile import (
    LOSSY_FOR_STATE_ONLY,
    decode_finding_outcome,
)
from cleartrace_core_api.interop.validation import validate_oscal_document, validate_references
from jsonschema import Draft202012Validator

pytestmark = pytest.mark.trl5


def _load_cyclonedx_schema() -> dict:
    cache = Path(".cache/cyclonedx-bom-1.6.schema.json")
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        from urllib.request import urlopen

        url = "https://raw.githubusercontent.com/CycloneDX/specification/master/schema/bom-1.6.schema.json"
        cache.write_bytes(urlopen(url, timeout=60).read())
    return json.loads(cache.read_text(encoding="utf-8"))


def test_t03_oscal_and_cyclonedx_exports() -> None:
    exporter = InteropExportService()
    dossiers = [
        exporter.dossier_from_seed(
            system_key="t03-a",
            name_en="System A",
            name_fr="Système A",
            findings_per_state=5,
        ),
        exporter.dossier_from_seed(
            system_key="t03-b",
            name_en="System B",
            name_fr="Système B",
            findings_per_state=5,
        ),
    ]
    validated = 0
    preserved_total = 0
    finding_total = 0
    states_seen: set[OutcomeState] = set()
    lossy_status_only = 0
    lossy_expected = 0
    for dossier in dossiers:
        raw = exporter.export_oscal("assessment-results", dossier)
        doc = json.loads(raw)
        validate_oscal_document(doc)
        dangling = validate_references(doc)
        assert dangling == []
        validated += 1
        expected = {u: OutcomeState(v) for u, v in dossier["source_outcomes"].items()}
        assert "source_outcomes" not in raw.decode()
        preserved, total = exporter.outcome_states_preserved(doc, expected)
        preserved_total += preserved
        finding_total += total
        states_seen.update(expected.values())
        # Lossy fields: a consumer that reads only target.status loses exactly the
        # states the profile reports as lossy, and no others.
        for finding in doc["assessment-results"]["results"][0]["findings"]:
            status_only = {k: v for k, v in finding.items() if k != "props"}
            source = expected[finding["uuid"]]
            if source in LOSSY_FOR_STATE_ONLY:
                lossy_expected += 1
                if decode_finding_outcome(status_only) is None:
                    lossy_status_only += 1
            else:
                assert decode_finding_outcome(status_only) == source
        cyclone = json.loads(exporter.export_cyclonedx(dossier["system"]))
        schema = _load_cyclonedx_schema()
        Draft202012Validator(schema).validate(cyclone)

    caps = exporter.capabilities()
    assert caps["five_state_profile"]["understood"] is True
    note = caps["five_state_profile"]["lossy_export_note"]
    for state in LOSSY_FOR_STATE_ONLY:
        assert state.value.replace("_", "-") in note, f"lossy note omits {state.value}"
    assert lossy_expected == 30 and lossy_status_only == 30
    assert states_seen == set(OutcomeState)

    assert validated == 2
    assert finding_total == 50
    assert preserved_total == 50


def test_t03_independent_importer_reads_profile() -> None:
    from trestle.oscal.assessment_results import Model as AssessmentResultsModel

    exporter = InteropExportService()
    dossier = exporter.dossier_from_seed(
        system_key="t03-import",
        name_en="Import",
        name_fr="Importation",
        findings_per_state=5,
    )
    raw = exporter.export_oscal("assessment-results", dossier)
    parsed = AssessmentResultsModel.model_validate_json(raw)
    findings = parsed.assessment_results.results[0].findings or []
    assert len(findings) == 25
    outcome_props = [p for f in findings for p in (f.props or []) if p.name == "outcome-state"]
    assert len(outcome_props) == 15
