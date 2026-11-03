package cleartrace.evidence

import rego.v1

has_valid_evidence(evidence_type) if {
    some artifact in input.evidence
    artifact.type == evidence_type
    artifact.authorized_submitter == true
    artifact.valid_until != "expired"
}

# Boolean coercion for objective payloads (undefined `passed` breaks object literals).
evidence_passed(evidence_type) := true if {
    has_valid_evidence(evidence_type)
}

evidence_passed(evidence_type) := false if {
    not has_valid_evidence(evidence_type)
}

missing_mandatory(spec) if {
    spec.required == true
    not has_valid_evidence(spec.type)
}

unauthorized_submitter(spec) if {
    some artifact in input.evidence
    artifact.type == spec.type
    artifact.authorized_submitter == false
}

stale_evidence(spec) if {
    some artifact in input.evidence
    artifact.type == spec.type
    artifact.valid_until == "expired"
}

evidence_issues contains issue if {
    some spec in input.evidence_specs
    missing_mandatory(spec)
    issue := "EVIDENCE_MISSING"
}

evidence_issues contains issue if {
    some spec in input.evidence_specs
    unauthorized_submitter(spec)
    issue := "SUBMITTER_UNAUTHORIZED"
}

evidence_issues contains issue if {
    some spec in input.evidence_specs
    stale_evidence(spec)
    issue := "EVIDENCE_STALE"
}

evidence_issue_list := [issue | some issue in evidence_issues]
