package cleartrace.aia

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-AIA-SCORE-01"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "aia_score",
			"applicable": true,
			"passed": evidence.evidence_passed("aia_record"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}
