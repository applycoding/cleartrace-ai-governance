from __future__ import annotations

from pathlib import Path

from cleartrace_audit.ledger import AuditLedgerService
from cleartrace_evidence.reviewer import ReviewerWorkflow
from cleartrace_evidence.store import EvidenceStoreService
from fastapi import Request


def get_evidence_store(request: Request) -> EvidenceStoreService:
    settings = request.app.state.settings
    return EvidenceStoreService(Path(settings.evidence_storage_root))


def get_audit_ledger(request: Request) -> AuditLedgerService:
    settings = request.app.state.settings
    return AuditLedgerService(
        worm_root=Path(settings.audit_worm_root),
        signer_key_path=Path(settings.audit_signer_key_path),
    )


def get_reviewer(request: Request) -> ReviewerWorkflow:
    _ = request
    return ReviewerWorkflow()
