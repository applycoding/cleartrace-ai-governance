package cleartrace.nist_ai_rmf

import rego.v1

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
		"key": "gv_mapping",
		"applicable": true,
		"passed": true,
		"critical_gate": false,
	}],
	"evidence_issues": [],
} if {
	input.control_key == "NIST-AI-RMF-GV-1.1"
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
