package cleartrace.dadm

import rego.v1
import data.cleartrace.evidence

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

evaluation := result if {
	input.control_key == "CA-DADM-6-1-1"
	result := aia_before_production
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-7"
	result := peer_review_by_level
}

evaluation := result if {
	input.control_key == "CA-DADM-APP-C-03"
	result := appendix_c_peer_review
}

aia_before_production := {
	"applicability_known": true,
	"applicability": applicable_production,
	"objectives": objectives_aia_record,
	"evidence_issues": evidence.evidence_issue_list,
} if applicable_production

aia_before_production := not_applicable if not applicable_production

peer_review_by_level := {
	"applicability_known": true,
	"applicability": applicable_production,
	"objectives": objectives_peer_generic,
	"evidence_issues": evidence.evidence_issue_list,
} if applicable_production

peer_review_by_level := not_applicable if not applicable_production

appendix_c_peer_review := {
	"applicability_known": true,
	"applicability": applicable_level_3,
	"objectives": objectives_appendix_c,
	"evidence_issues": evidence.evidence_issue_list,
} if applicable_level_3

appendix_c_peer_review := not_applicable if not applicable_level_3

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

applicable_production if {
	input.system.planned_production_use == true
}

applicable_level_3 if {
	applicable_production
	input.system.impact_level >= 3
}

objectives_aia_record := [{
	"key": "aia_record",
	"applicable": true,
	"passed": evidence.evidence_passed("aia_record"),
	"critical_gate": true,
}]

# Clause 6.3.7 expects peer review and an AIA on file before production; both are
# non-critical gates so one can pass while the other fails (partially_met).
objectives_peer_generic := [
	{
		"key": "peer_review",
		"applicable": true,
		"passed": evidence.evidence_passed("peer_review_report"),
		"critical_gate": false,
	},
	{
		"key": "aia_record",
		"applicable": true,
		"passed": evidence.evidence_passed("aia_record"),
		"critical_gate": false,
	},
]

objectives_appendix_c := [{
	"key": "peer_review",
	"applicable": true,
	"passed": evidence.evidence_passed("peer_review_report"),
	"critical_gate": true,
}]
