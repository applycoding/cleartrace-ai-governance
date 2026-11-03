package cleartrace.golden

import rego.v1

default evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
} if {
	input.scenario == "na"
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{"key": "o", "applicable": true, "passed": true, "critical_gate": false}],
	"evidence_issues": [],
} if {
	input.scenario == "met"
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [
		{"key": "pass", "applicable": true, "passed": true, "critical_gate": false},
		{"key": "fail", "applicable": true, "passed": false, "critical_gate": false},
	],
	"evidence_issues": [],
} if {
	input.scenario == "pm"
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{"key": "cg", "applicable": true, "passed": false, "critical_gate": false}],
	"evidence_issues": [],
} if {
	input.scenario == "nm_fail"
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{"key": "cg", "applicable": true, "passed": false, "critical_gate": true}],
	"evidence_issues": ["EVIDENCE_MISSING"],
} if {
	input.scenario == "nm_critical_missing"
}

evaluation := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{"key": "ok", "applicable": true, "passed": true, "critical_gate": false}],
	"evidence_issues": ["EVIDENCE_MISSING"],
} if {
	input.scenario == "utd_missing"
}
