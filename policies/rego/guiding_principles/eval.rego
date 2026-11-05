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
	result := principle_eval("principle_1_impacts")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-02"
	result := principle_eval("principle_2_transparency")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-03"
	result := principle_eval("principle_3_explanations")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-06"
	result := principle_eval("principle_6_human_rights")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-08"
	result := principle_eval("principle_8_privacy_security")
}

evaluation := result if {
	input.control_key == "CA-AI-PRIN-09"
	result := principle_eval("principle_9_oversight")
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
} if {
	input.system.planned_production_use == true
}

principle_eval(key) := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
} if {
	input.system.planned_production_use != true
}
