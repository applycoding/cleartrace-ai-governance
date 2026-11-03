package cleartrace.dsd

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{
		"key": "canadian_facilities",
		"applicable": true,
		"passed": evidence.evidence_passed("canadian_facility_assessment"),
		"critical_gate": false,
	}],
	"evidence_issues": evidence.evidence_issue_list,
} if {
	input.control_key == "CA-DSD-4-3-24"
	input.system.planned_production_use == true
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
