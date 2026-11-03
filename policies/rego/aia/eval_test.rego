package cleartrace.aia

import rego.v1

test_aia_control_met_with_record if {
	result := evaluation with input as {
		"control_key": "CA-AIA-SCORE-01",
		"system": {"planned_production_use": true},
		"evidence": [{"type": "aia_record", "authorized_submitter": true, "valid_until": "2099-01-01"}],
		"evidence_specs": [{"type": "aia_record", "required": true}],
	}
	result.objectives[0].passed == true
}
