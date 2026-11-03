from __future__ import annotations

from enum import StrEnum

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class ArtefactClass(StrEnum):
    CONTROL_MAPPING = "control_mapping"
    ASSESSMENT_RECORD = "assessment_record"
    EVIDENCE_REFERENCE = "evidence_reference"
    APPROVAL = "approval"
    EXCEPTION = "exception"
    ATTESTATION = "attestation"
    REMEDIATION_ACTION = "remediation_action"
    AUDIT_HISTORY = "audit_history"


ARTEFACT_CLASSES: frozenset[str] = frozenset(c.value for c in ArtefactClass)


DEFAULT_REQUIRED_ROLES: dict[str, tuple[str, ...]] = {
    ArtefactClass.CONTROL_MAPPING.value: ("assessor", "policy_steward"),
    ArtefactClass.ASSESSMENT_RECORD.value: ("assessor",),
    ArtefactClass.EVIDENCE_REFERENCE.value: ("system_owner", "assessor"),
    ArtefactClass.APPROVAL.value: ("approver",),
    ArtefactClass.EXCEPTION.value: ("oversight_reviewer", "tenant_admin"),
    ArtefactClass.ATTESTATION.value: ("system_owner", "approver"),
    ArtefactClass.REMEDIATION_ACTION.value: ("system_owner", "assessor"),
    ArtefactClass.AUDIT_HISTORY.value: ("auditor", "tenant_admin"),
}
