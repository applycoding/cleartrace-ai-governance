package cleartrace.dsd

import rego.v1

test_dsd if {
	evaluation with input as {"control_key": "CA-DSD-4-3-24", "system": {"planned_production_use": true}, "evidence": [], "evidence_specs": []}
}
