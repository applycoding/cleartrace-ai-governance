package cleartrace.dadm

test_not_applicable {
    outcome with input as {"applicability": false}
    outcome == "not_applicable"
}

test_not_met {
    outcome with input as {"critical_gate_failed": true, "applicability": true}
    outcome == "not_met"
}

test_met {
    outcome with input as {"all_pass": true, "applicability": true}
    outcome == "met"
}
