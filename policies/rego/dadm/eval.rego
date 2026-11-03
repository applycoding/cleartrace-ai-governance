package cleartrace.dadm

import data.cleartrace.evidence
import rego.v1

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

evaluation := result if {
	input.control_key == "CA-DADM-6-3-8"
	result := gba_plus_elements
}

aia_before_production := {
	"applicability_known": true,
	"applicability": applicable_production,
	"objectives": objectives_aia_record,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

aia_before_production := not_applicable if not applicable_production

peer_review_by_level := {
	"applicability_known": true,
	"applicability": applicable_production,
	"objectives": objectives_peer_generic,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

peer_review_by_level := not_applicable if not applicable_production

appendix_c_peer_review := {
	"applicability_known": true,
	"applicability": applicable_level_3,
	"objectives": objectives_appendix_c,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_level_3
}

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

objectives_peer_generic := [{
	"key": "peer_review",
	"applicable": true,
	"passed": evidence.evidence_passed("peer_review_report"),
	"critical_gate": false,
}]

objectives_appendix_c := [{
	"key": "peer_review",
	"applicable": true,
	"passed": evidence.evidence_passed("peer_review_report"),
	"critical_gate": true,
}]

# DADM 6.3.8 and Appendix C: for impact Levels II-IV the Gender-based Analysis Plus
# must have been consulted with the department's diversity and inclusion experts and
# include an assessment of impacts on different population groups and details of
# measures for the risks identified. Level I has no GBA+ requirement. Each required
# element is a separate objective, so a record that covers some but not all of them
# yields mixed objective results.
gba_plus_elements := {
	"applicability_known": true,
	"applicability": applicable_gba_plus,
	"objectives": objectives_gba_plus,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_gba_plus
}

gba_plus_elements := not_applicable if not applicable_gba_plus

applicable_gba_plus if {
	applicable_production
	input.system.impact_level >= 2
}

gba_plus_required_elements := [
	"population_impact_assessment",
	"di_experts_consulted",
	"mitigation_measures",
]

objectives_gba_plus := [obj |
	some element in gba_plus_required_elements
	obj := {
		"key": element,
		"applicable": true,
		"passed": gba_plus_covers(element),
		"critical_gate": false,
	}
]

gba_plus_covers(element) if {
	gba_plus_has_element(element)
}

gba_plus_covers(element) := false if {
	not gba_plus_has_element(element)
}

gba_plus_has_element(element) if {
	some artifact in input.evidence
	artifact.type == "gba_plus_record"
	artifact.authorized_submitter == true
	artifact.valid_until != "expired"
	element in artifact.covers
}
