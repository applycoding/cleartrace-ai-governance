from __future__ import annotations

from cleartrace_contracts.models import OutcomeState

OSCAL_NAMESPACE = "urn:trivision:oscal:ns:goc-ai-gov"


def map_outcome_to_oscal(state: OutcomeState) -> dict[str, object]:
    """Blueprint section 10.2 five-state profile mapping."""
    match state:
        case OutcomeState.MET:
            return {
                "status": {"state": "satisfied", "reason": "pass"},
                "props": [],
            }
        case OutcomeState.PARTIALLY_MET:
            return {
                "status": {"state": "not-satisfied", "reason": "other"},
                "props": [
                    {
                        "name": "outcome-state",
                        "ns": OSCAL_NAMESPACE,
                        "value": "partially-met",
                    }
                ],
            }
        case OutcomeState.NOT_MET:
            return {
                "status": {"state": "not-satisfied", "reason": "fail"},
                "props": [],
            }
        case OutcomeState.NOT_APPLICABLE:
            return {
                "status": {"state": "satisfied", "reason": "other"},
                "props": [
                    {"name": "outcome-state", "ns": OSCAL_NAMESPACE, "value": "not-applicable"},
                ],
            }
        case OutcomeState.UNABLE_TO_DETERMINE:
            return {
                "status": {"state": "not-satisfied", "reason": "other"},
                "props": [
                    {
                        "name": "outcome-state",
                        "ns": OSCAL_NAMESPACE,
                        "value": "unable-to-determine",
                    },
                ],
            }
        case _:
            raise AssertionError(f"Unhandled outcome state: {state!r}")
