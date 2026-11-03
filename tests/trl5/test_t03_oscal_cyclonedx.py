from __future__ import annotations

import json
from pathlib import Path

import pytest
from cleartrace_core_api.interop.exporter import InteropExportService
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
        exporter.dossier_from_seed(system_key="t03-a", name_en="System A", name_fr="Système A"),
        exporter.dossier_from_seed(system_key="t03-b", name_en="System B", name_fr="Système B"),
    ]
    validated = 0
    preserved_total = 0
    finding_total = 0
    for dossier in dossiers:
        raw = exporter.export_oscal("assessment-results", dossier)
        doc = json.loads(raw)
        validate_oscal_document(doc)
        dangling = validate_references(doc)
        assert dangling == []
        validated += 1
        preserved, total = exporter.outcome_states_preserved(doc)
        preserved_total += preserved
        finding_total += total
        cyclone = json.loads(exporter.export_cyclonedx(dossier["system"]))
        schema = _load_cyclonedx_schema()
        Draft202012Validator(schema).validate(cyclone)

    caps = exporter.capabilities()
    assert caps["five_state_profile"]["understood"] is True
    assert "lossy" in caps["five_state_profile"]["lossy_export_note"]

    assert validated == 2
    assert finding_total == 10
    assert preserved_total == finding_total


def test_t03_independent_importer_reads_profile() -> None:
    from trestle.oscal.assessment_results import Model as AssessmentResultsModel

    exporter = InteropExportService()
    dossier = exporter.dossier_from_seed(
        system_key="t03-import",
        name_en="Import",
        name_fr="Importation",
    )
    raw = exporter.export_oscal("assessment-results", dossier)
    parsed = AssessmentResultsModel.model_validate_json(raw)
    findings = parsed.assessment_results.results[0].findings or []
    assert len(findings) == 5
    outcome_props = [p for f in findings for p in (f.props or []) if p.name == "outcome-state"]
    assert len(outcome_props) == 3
