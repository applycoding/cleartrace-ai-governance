package cleartrace.ai_strategy

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-GC-AI-P4-REGISTER"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "ai_register",
			"applicable": true,
			"passed": evidence.evidence_passed("ai_register_entry"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}
