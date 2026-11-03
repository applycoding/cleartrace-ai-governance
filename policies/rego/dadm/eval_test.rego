package cleartrace.dadm

import rego.v1

test_appendix_c_not_met_without_evidence if {
	result := evaluation with input as {
		"control_key": "CA-DADM-APP-C-03",
		"system": {"planned_production_use": true, "impact_level": 3},
		"evidence": [],
		"evidence_specs": [{"type": "peer_review_report", "required": true}],
	}
	count(result.objectives) == 1
	result.objectives[0].passed == false
}
