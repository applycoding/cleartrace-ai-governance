package cleartrace.ai_strategy

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
		"key": "register_alignment",
		"applicable": true,
		"passed": evidence.evidence_passed("ai_register_entry"),
		"critical_gate": false,
	}],
	"evidence_issues": evidence.evidence_issue_list,
} if {
	input.control_key == "CA-GC-AI-P4-REGISTER"
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
