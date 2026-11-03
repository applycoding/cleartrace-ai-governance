from __future__ import annotations

from cleartrace_contracts.models import OutcomeState
from cleartrace_core_api.interop.oscal_profile import OUTCOME_TO_OSCAL, build_finding_props


def test_five_state_profile_mappings() -> None:
    for state in OutcomeState:
        mapping = OUTCOME_TO_OSCAL[state]
        assert "status_state" in mapping
        assert "reason" in mapping
    props = build_finding_props(OutcomeState.NOT_APPLICABLE)
    assert props[0]["name"] == "outcome-state"
    assert props[0]["value"] == "not-applicable"
