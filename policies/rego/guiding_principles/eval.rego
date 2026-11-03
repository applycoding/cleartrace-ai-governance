package cleartrace.guiding_principles

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-01"
	result := principle_eval("principle_1_alignment")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-02"
	result := principle_eval("principle_2_transparency")
}

principle_eval(key) := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{
		"key": key,
		"applicable": true,
		"passed": evidence.evidence_passed("principle_alignment_record"),
		"critical_gate": false,
	}],
	"evidence_issues": evidence.evidence_issue_list,
}

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}
