"""Audit privileged reads (blueprint section 8: admin, support and export reads)."""

from __future__ import annotations

import logging

from cleartrace_db.session import tenant_transaction
from fastapi import HTTPException, Request

from cleartrace_core_api.deps import get_audit_ledger

_LOG = logging.getLogger(__name__)


def record_privileged_read(
    request: Request,
    *,
    action: str,
    resource_type: str,
    payload: dict[str, object],
) -> None:
    """Write the audit event for a privileged read before its data is returned.

    The read fails closed: if the audit event cannot be written, the caller gets a
    503 problem response instead of unaudited data.
    """
    auth = request.state.auth
    settings = request.app.state.settings
    ledger = get_audit_ledger(request)
    try:
        with tenant_transaction(settings.database_url, auth.tenant_id) as conn:
            ledger.append_event_tx(
                conn,
                tenant_id=auth.tenant_id,
                actor_id=auth.actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=None,
                payload={"path": request.url.path, **payload},
                pii_plaintext=None,
            )
    except Exception as exc:
        _LOG.exception(
            "privileged read audit write failed",
            extra={"tenant_id": str(auth.tenant_id), "audit_action": action},
        )
        raise HTTPException(
            status_code=503, detail="The privileged read could not be audited"
        ) from exc
