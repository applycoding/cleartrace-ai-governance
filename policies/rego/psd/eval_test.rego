package cleartrace.psd

import rego.v1

test_psd_control if {
	evaluation with input as {
		"control_key": "CA-PSD-4-1-28",
		"system": {"planned_production_use": true},
		"evidence": [],
		"evidence_specs": [{"type": "adm_accountability_record", "required": true}],
	}
}
