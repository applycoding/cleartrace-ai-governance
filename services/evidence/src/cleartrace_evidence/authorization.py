from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from psycopg import Connection

from cleartrace_evidence.constants import DEFAULT_REQUIRED_ROLES


def role_at_submission(
    conn: Connection[Any],
    *,
    tenant_id: UUID,
    principal_id: UUID,
    at_time: datetime | None = None,
) -> str | None:
    when = at_time or datetime.now(tz=UTC)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role_code
            FROM role_assignment
            WHERE tenant_id = %s
              AND principal_id = %s
              AND valid_from <= %s
              AND (valid_to IS NULL OR valid_to > %s)
              AND superseded_at IS NULL
            ORDER BY valid_from DESC
            LIMIT 1
            """,
            (tenant_id, principal_id, when, when),
        )
        row = cur.fetchone()
    return str(row[0]) if row else None


def is_authorized_submitter(
    conn: Connection[Any],
    *,
    tenant_id: UUID,
    artefact_class: str,
    submitter_role: str | None,
) -> bool:
    if submitter_role is None:
        return False
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT required_roles
            FROM evidence_spec
            WHERE tenant_id = %s AND artefact_class = %s
            """,
            (tenant_id, artefact_class),
        )
        row = cur.fetchone()
    required = DEFAULT_REQUIRED_ROLES.get(artefact_class, ()) if row is None else tuple(row[0])
    return submitter_role in required


def ensure_evidence_specs(conn: Connection[Any], tenant_id: UUID) -> None:
    from cleartrace_evidence.constants import ARTEFACT_CLASSES, DEFAULT_REQUIRED_ROLES

    with conn.cursor() as cur:
        for artefact_class in ARTEFACT_CLASSES:
            roles = list(DEFAULT_REQUIRED_ROLES.get(artefact_class, ("system_owner",)))
            cur.execute(
                """
                INSERT INTO evidence_spec (id, tenant_id, artefact_class, required_roles, mandatory)
                VALUES (gen_random_uuid(), %s, %s, %s, true)
                ON CONFLICT (tenant_id, artefact_class) DO NOTHING
                """,
                (tenant_id, artefact_class, roles),
            )


def satisfies_mandatory_spec(
    conn: Connection[Any],
    *,
    tenant_id: UUID,
    evidence_version_id: UUID,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ea.artefact_class, ev.authorized_submitter, ev.quarantined, es.mandatory
            FROM evidence_version ev
            JOIN evidence_artefact ea ON ea.id = ev.evidence_artefact_id
            LEFT JOIN evidence_spec es
              ON es.tenant_id = ev.tenant_id AND es.artefact_class = ea.artefact_class
            WHERE ev.tenant_id = %s AND ev.id = %s
            """,
            (tenant_id, evidence_version_id),
        )
        row = cur.fetchone()
    if row is None:
        return False
    _artefact_class, authorized, quarantined, mandatory = row
    if not mandatory:
        return True
    return bool(authorized) and not bool(quarantined)
