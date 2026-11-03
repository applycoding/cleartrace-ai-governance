package cleartrace.aia

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
		"key": "aia_score_valid",
		"applicable": true,
		"passed": evidence.evidence_passed("aia_record"),
		"critical_gate": false,
	}],
	"evidence_issues": evidence.evidence_issue_list,
} if {
	input.control_key == "CA-AIA-SCORE-01"
	input.system.planned_production_use == true
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
