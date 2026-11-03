package cleartrace.dadm

default outcome := "unable_to_determine"

outcome := "not_applicable" {
    input.applicability == false
}

outcome := "not_met" {
    input.critical_gate_failed
}

outcome := "unable_to_determine" {
    input.evidence_missing
}

outcome := "partially_met" {
    input.partial_pass
}

outcome := "met" {
    input.all_pass
}
