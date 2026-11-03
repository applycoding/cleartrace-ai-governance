from __future__ import annotations

from cleartrace_contracts.models import OutcomeState

OSCAL_PROFILE_NS = "urn:trivision:oscal:ns:goc-ai-gov"
LOSSY_NOTE = (
    "lossy-for-state-only-consumers: not-applicable findings map to satisfied/pass; "
    "use prop outcome-state for all five ClearTrace states."
)

OUTCOME_TO_OSCAL: dict[OutcomeState, dict[str, str]] = {
    OutcomeState.MET: {"status_state": "satisfied", "reason": "pass"},
    OutcomeState.PARTIALLY_MET: {
        "status_state": "not-satisfied",
        "reason": "other",
        "outcome_state": "partially-met",
    },
    OutcomeState.NOT_MET: {"status_state": "not-satisfied", "reason": "fail"},
    OutcomeState.NOT_APPLICABLE: {
        "status_state": "satisfied",
        "reason": "other",
        "outcome_state": "not-applicable",
    },
    OutcomeState.UNABLE_TO_DETERMINE: {
        "status_state": "not-satisfied",
        "reason": "other",
        "outcome_state": "unable-to-determine",
    },
}


def build_finding_props(outcome: OutcomeState) -> list[dict[str, str]]:
    mapping = OUTCOME_TO_OSCAL[outcome]
    props: list[dict[str, str]] = []
    if "outcome_state" in mapping:
        props.append(
            {
                "name": "outcome-state",
                "ns": OSCAL_PROFILE_NS,
                "value": mapping["outcome_state"],
            }
        )
    return props
