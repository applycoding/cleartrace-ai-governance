package cleartrace.psd

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-PSD-4-1-28"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "accountability",
			"applicable": true,
			"passed": evidence.evidence_passed("adm_accountability_record"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}

evaluation := result if {
	input.control_key == "CA-PSD-4-1-26"
	input.system.planned_production_use == true
	result := {
		"applicability_known": true,
		"applicability": true,
		"objectives": [{
			"key": "design_by_default",
			"applicable": true,
			"passed": evidence.evidence_passed("design_by_default_record"),
			"critical_gate": true,
		}],
		"evidence_issues": evidence.evidence_issue_list,
	}
}
