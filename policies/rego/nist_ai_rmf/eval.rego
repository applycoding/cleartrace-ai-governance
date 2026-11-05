package cleartrace.nist_ai_rmf

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "NIST-AI-RMF-GV-1.1"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "nist_govern_record",
			"applicable": true,
			"passed": evidence.evidence_passed("nist_govern_record"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}
