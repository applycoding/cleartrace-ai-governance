package cleartrace.dsd

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-DSD-4-3-24"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "canadian_facility",
			"applicable": true,
			"passed": evidence.evidence_passed("canadian_facility_assessment"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}
