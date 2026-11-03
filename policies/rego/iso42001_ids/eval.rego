package cleartrace.iso42001_ids

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
		"key": "policy_identifier",
		"applicable": true,
		"passed": true,
		"critical_gate": false,
	}],
	"evidence_issues": [],
} if {
	input.control_key == "ISO-42001-AI-POLICY"
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
