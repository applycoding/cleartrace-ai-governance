package cleartrace.golden

import rego.v1

test_met if {
	evaluation.applicability == true with input as {"scenario": "met"}
}

test_na if {
	evaluation.applicability == false with input as {"scenario": "na"}
}
