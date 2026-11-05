package cleartrace.dadm

import data.cleartrace.evidence
import rego.v1

default evaluation := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

# --- single-evidence critical gates (production blockers) ---

evaluation := result if {
	input.control_key == "CA-DADM-6-1-1"
	result := production_critical("aia_record", "aia_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-1-3"
	result := production_critical("aia_update", "aia_update_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-2-7"
	result := production_critical("decision_trace", "decision_trace_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-1"
	result := production_critical("preprod_testing", "preprod_test_report")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-2"
	result := production_critical("monitoring", "monitoring_schedule_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-3"
	result := production_critical("human_rights", "human_rights_attestation")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-5"
	result := production_critical("dataset_validation", "dataset_validation_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-6"
	result := production_critical("data_governance", "data_governance_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-10"
	result := production_critical("security_risk", "security_risk_assessment")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-11"
	result := production_critical("integrity", "integrity_controls_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-12"
	result := production_critical("legal_consult", "legal_consultation_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-3-14"
	result := production_critical("operational_approval", "operational_approval_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-4-1"
	result := production_critical("recourse", "recourse_notice_record")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-5-1"
	result := production_critical("effectiveness_pub", "effectiveness_publication")
}

evaluation := result if {
	input.control_key == "CA-DADM-6-5-2"
	result := production_critical("fairness_pub", "fairness_publication")
}

# --- notice: multi-channel (Appendix C row 1) ---

evaluation := result if {
	input.control_key == "CA-DADM-6-2-1"
	result := notice_channels
}

# --- explanation: multi-element by level (Appendix C row 2) ---

evaluation := result if {
	input.control_key == "CA-DADM-6-2-3"
	result := explanation_elements
}

# --- peer review 6.3.7: Levels II+ (Appendix C Level I = none) ---

evaluation := result if {
	input.control_key == "CA-DADM-6-3-7"
	result := peer_review_by_level
}

# --- Appendix C row 3 Levels III-IV ---

evaluation := result if {
	input.control_key == "CA-DADM-APP-C-03"
	result := appendix_c_peer_review
}

# --- GBA+ multi-element Levels II-IV ---

evaluation := result if {
	input.control_key == "CA-DADM-6-3-8"
	result := gba_plus_elements
}

# --- training multi-element by level ---

evaluation := result if {
	input.control_key == "CA-DADM-6-3-9"
	result := training_elements
}

# --- human involvement multi-element by level ---

evaluation := result if {
	input.control_key == "CA-DADM-6-3-13"
	result := human_involvement_elements
}

# ---------- helpers ----------

not_applicable := {
	"applicability_known": true,
	"applicability": false,
	"objectives": [],
	"evidence_issues": [],
}

applicable_production if {
	input.system.planned_production_use == true
}

production_critical(key, evidence_type) := {
	"applicability_known": true,
	"applicability": true,
	"objectives": [{
		"key": key,
		"applicable": true,
		"passed": evidence.evidence_passed(evidence_type),
		"critical_gate": true,
	}],
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

production_critical(key, evidence_type) := not_applicable if not applicable_production

# Notice channels: web, in_person, mail, telephone. Level III+ also needs explanation_link.
notice_required_elements := ["web", "in_person", "mail", "telephone"] if {
	input.system.impact_level < 3
}

notice_required_elements := ["web", "in_person", "mail", "telephone", "explanation_link"] if {
	input.system.impact_level >= 3
}

notice_channels := {
	"applicability_known": true,
	"applicability": true,
	"objectives": notice_objectives,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

notice_channels := not_applicable if not applicable_production

notice_objectives := [obj |
	some element in notice_required_elements
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("notice_record", element),
		"critical_gate": false,
	}
]

# Explanation: Level I general only; Levels II-IV add individualized denial explanation.
explanation_required_elements := ["general_public"] if {
	input.system.impact_level <= 1
}

explanation_required_elements := ["general_public", "individualized_denial"] if {
	input.system.impact_level >= 2
}

explanation_elements := {
	"applicability_known": true,
	"applicability": true,
	"objectives": explanation_objectives,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

explanation_elements := not_applicable if not applicable_production

explanation_objectives := [obj |
	some element in explanation_required_elements
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("explanation_record", element),
		"critical_gate": false,
	}
]

# Peer review 6.3.7: Level I none; Level II-III one expert; Level IV two experts.
peer_review_by_level := {
	"applicability_known": true,
	"applicability": true,
	"objectives": peer_objectives_generic,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
	input.system.impact_level >= 2
	input.system.impact_level <= 3
}

peer_review_by_level := {
	"applicability_known": true,
	"applicability": true,
	"objectives": peer_objectives_level_iv,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
	input.system.impact_level >= 4
}

peer_review_by_level := not_applicable if {
	not applicable_production
}

peer_review_by_level := not_applicable if {
	applicable_production
	input.system.impact_level < 2
}

peer_objectives_generic := [{
	"key": "peer_review",
	"applicable": true,
	"passed": evidence.evidence_passed("peer_review_report"),
	"critical_gate": false,
}]

peer_objectives_level_iv := [obj |
	some element in ["expert_1", "expert_2"]
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("peer_review_report", element),
		"critical_gate": false,
	}
]

# Appendix C Levels III-IV peer review is a critical gate.
appendix_c_peer_review := {
	"applicability_known": true,
	"applicability": true,
	"objectives": appendix_c_objectives,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
	input.system.impact_level >= 3
	input.system.impact_level <= 3
}

appendix_c_peer_review := {
	"applicability_known": true,
	"applicability": true,
	"objectives": peer_objectives_level_iv_critical,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
	input.system.impact_level >= 4
}

appendix_c_peer_review := not_applicable if {
	not applicable_production
}

appendix_c_peer_review := not_applicable if {
	applicable_production
	input.system.impact_level < 3
}

appendix_c_objectives := [{
	"key": "peer_review",
	"applicable": true,
	"passed": evidence.evidence_passed("peer_review_report"),
	"critical_gate": true,
}]

peer_objectives_level_iv_critical := [obj |
	some element in ["expert_1", "expert_2"]
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("peer_review_report", element),
		"critical_gate": true,
	}
]

# GBA+ Levels II-IV
gba_plus_elements := {
	"applicability_known": true,
	"applicability": true,
	"objectives": objectives_gba_plus,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
	input.system.impact_level >= 2
}

gba_plus_elements := not_applicable if {
	not applicable_production
}

gba_plus_elements := not_applicable if {
	applicable_production
	input.system.impact_level < 2
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
		"passed": record_covers("gba_plus_record", element),
		"critical_gate": false,
	}
]

# Training: Levels I-II high-level; Levels III-IV recurring technical topics.
training_required_elements := ["usage_explanation"] if {
	input.system.impact_level <= 2
}

training_required_elements := ["technical", "privacy_fairness_rights", "evaluate_override"] if {
	input.system.impact_level >= 3
}

training_elements := {
	"applicability_known": true,
	"applicability": true,
	"objectives": training_objectives,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

training_elements := not_applicable if not applicable_production

training_objectives := [obj |
	some element in training_required_elements
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("training_record", element),
		"critical_gate": false,
	}
]

# Human involvement: Levels I-II QA; Levels III-IV final human decision + QA.
human_required_elements := ["qa_involvement"] if {
	input.system.impact_level <= 2
}

human_required_elements := ["final_human_decision", "qa_involvement"] if {
	input.system.impact_level >= 3
}

human_involvement_elements := {
	"applicability_known": true,
	"applicability": true,
	"objectives": human_objectives,
	"evidence_issues": evidence.evidence_issue_list,
} if {
	applicable_production
}

human_involvement_elements := not_applicable if not applicable_production

human_objectives := [obj |
	some element in human_required_elements
	obj := {
		"key": element,
		"applicable": true,
		"passed": record_covers("human_involvement_record", element),
		"critical_gate": false,
	}
]

# Shared "covers" helper for multi-element evidence records.
record_covers(evidence_type, element) if {
	some artifact in input.evidence
	artifact.type == evidence_type
	artifact.authorized_submitter == true
	artifact.valid_until != "expired"
	element in artifact.covers
}

record_covers(evidence_type, element) := false if {
	not record_has_element(evidence_type, element)
}

record_has_element(evidence_type, element) if {
	some artifact in input.evidence
	artifact.type == evidence_type
	artifact.authorized_submitter == true
	artifact.valid_until != "expired"
	element in artifact.covers
}
