from __future__ import annotations

from cleartrace_contracts.models import OutcomeState

OSCAL_PROFILE_NS = "urn:trivision:oscal:ns:goc-ai-gov"
LOSSY_NOTE = (
    "lossy-for-state-only-consumers: partially-met and unable-to-determine both map to "
    "not-satisfied/other and not-applicable maps to satisfied/other; "
    "use prop outcome-state for all five ClearTrace states."
)

# Outcome states that a consumer reading only target.status cannot recover.
LOSSY_FOR_STATE_ONLY: frozenset[OutcomeState] = frozenset(
    {OutcomeState.PARTIALLY_MET, OutcomeState.NOT_APPLICABLE, OutcomeState.UNABLE_TO_DETERMINE}
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


_PROP_TO_OUTCOME: dict[str, OutcomeState] = {
    m["outcome_state"]: state for state, m in OUTCOME_TO_OSCAL.items() if "outcome_state" in m
}
_STATUS_TO_OUTCOME: dict[tuple[str, str], OutcomeState] = {
    (m["status_state"], m["reason"]): state
    for state, m in OUTCOME_TO_OSCAL.items()
    if "outcome_state" not in m
}


def decode_finding_outcome(finding: dict[str, object]) -> OutcomeState | None:
    """Read a ClearTrace outcome back from an exported OSCAL finding (profile reader).

    The outcome-state prop wins; without it only the two lossless status pairs
    (satisfied/pass, not-satisfied/fail) decode. Anything else returns None.
    """
    props = finding.get("props")
    if isinstance(props, list):
        for prop in props:
            if (
                isinstance(prop, dict)
                and prop.get("name") == "outcome-state"
                and prop.get("ns") == OSCAL_PROFILE_NS
            ):
                return _PROP_TO_OUTCOME.get(str(prop.get("value")))
    target = finding.get("target")
    status = target.get("status") if isinstance(target, dict) else None
    if not isinstance(status, dict):
        return None
    return _STATUS_TO_OUTCOME.get((str(status.get("state")), str(status.get("reason"))))
