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

gba_specs := [{"type": "gba_plus_record", "required": true}]

test_gba_plus_partial_record_mixes_objectives if {
	result := evaluation with input as {
		"control_key": "CA-DADM-6-3-8",
		"system": {"planned_production_use": true, "impact_level": 2},
		"evidence": [{
			"type": "gba_plus_record",
			"authorized_submitter": true,
			"valid_until": "2099-01-01",
			"covers": ["population_impact_assessment", "di_experts_consulted"],
		}],
		"evidence_specs": gba_specs,
	}
	result.applicability == true
	count(result.objectives) == 3
	passed := {o.key | some o in result.objectives; o.passed == true}
	passed == {"population_impact_assessment", "di_experts_consulted"}
	failed := {o.key | some o in result.objectives; o.passed == false}
	failed == {"mitigation_measures"}
	count(result.evidence_issues) == 0
}

test_gba_plus_complete_record_passes_all if {
	result := evaluation with input as {
		"control_key": "CA-DADM-6-3-8",
		"system": {"planned_production_use": true, "impact_level": 3},
		"evidence": [{
			"type": "gba_plus_record",
			"authorized_submitter": true,
			"valid_until": "2099-01-01",
			"covers": ["population_impact_assessment", "di_experts_consulted", "mitigation_measures"],
		}],
		"evidence_specs": gba_specs,
	}
	every o in result.objectives { o.passed == true }
	count(result.objectives) == 3
}

test_gba_plus_missing_record_reports_evidence_missing if {
	result := evaluation with input as {
		"control_key": "CA-DADM-6-3-8",
		"system": {"planned_production_use": true, "impact_level": 4},
		"evidence": [],
		"evidence_specs": gba_specs,
	}
	"EVIDENCE_MISSING" in result.evidence_issues
	every o in result.objectives { o.passed == false }
}

test_gba_plus_not_required_at_level_1 if {
	result := evaluation with input as {
		"control_key": "CA-DADM-6-3-8",
		"system": {"planned_production_use": true, "impact_level": 1},
		"evidence": [],
		"evidence_specs": gba_specs,
	}
	result.applicability == false
}
