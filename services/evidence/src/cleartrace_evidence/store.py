from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from psycopg import Connection
from uuid6 import uuid7

from cleartrace_evidence.authorization import (
    ensure_evidence_specs,
    is_authorized_submitter,
    role_at_submission,
    satisfies_mandatory_spec,
)
from cleartrace_evidence.constants import ARTEFACT_CLASSES, ArtefactClass
from cleartrace_evidence.lineage import lineage_to_rows
from cleartrace_evidence.scanner import scan_upload


class EvidenceStoreService:
    """Persists evidence artefacts with scanning, hashing and lineage."""

    def __init__(self, storage_root: Path) -> None:
        self._storage_root = storage_root
        self._storage_root.mkdir(parents=True, exist_ok=True)

    async def store_artefact(
        self,
        tenant_id: UUID,
        payload: bytes,
        metadata: dict[str, object],
    ) -> UUID:
        raise NotImplementedError("Use store_artefact_tx for transactional storage")

    def store_artefact_tx(
        self,
        conn: Connection[Any],
        *,
        tenant_id: UUID,
        principal_id: UUID,
        payload: bytes,
        metadata: dict[str, object],
        audit_append: Any,
    ) -> UUID:
        ensure_evidence_specs(conn, tenant_id)
        artefact_class = str(metadata.get("artefact_class", ""))
        if artefact_class not in ARTEFACT_CLASSES:
            msg = f"Unknown artefact class: {artefact_class}"
            raise ValueError(msg)

        media_type = str(metadata.get("media_type", "application/octet-stream"))
        scan = scan_upload(payload, media_type)
        if not scan.ok:
            raise ValueError(scan.reason_en)

        sha256 = hashlib.sha256(payload).hexdigest()
        collected_at_raw = metadata.get("collected_at")
        if isinstance(collected_at_raw, datetime):
            collected_at = collected_at_raw
        else:
            collected_at = datetime.now(tz=UTC)

        submitter_role = role_at_submission(
            conn, tenant_id=tenant_id, principal_id=principal_id, at_time=collected_at
        )
        authorized = is_authorized_submitter(
            conn,
            tenant_id=tenant_id,
            artefact_class=artefact_class,
            submitter_role=submitter_role,
        )
        quarantined = not authorized

        artefact_id = uuid7()
        version_id = uuid7()
        version_number = 1
        rel_path = Path(str(tenant_id)) / f"{version_id.hex}.bin"
        dest = self._storage_root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        storage_uri = f"file://{dest.resolve()}"

        title_en = str(metadata.get("title_en", "Evidence artefact"))
        title_fr = str(metadata.get("title_fr", "Artefact de preuve"))
        valid_until = metadata.get("valid_until")
        signature_present = bool(metadata.get("signature_present", False))

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO evidence_artefact (id, tenant_id, artefact_class, current_version_id)
                VALUES (%s, %s, %s, %s)
                """,
                (artefact_id, tenant_id, artefact_class, version_id),
            )
            cur.execute(
                """
                INSERT INTO evidence_version (
                  id, tenant_id, evidence_artefact_id, version_number,
                  sha256, storage_uri, media_type, title_en, title_fr,
                  submitted_by, submitter_role_at_time, authorized_submitter,
                  collected_at, valid_until, quarantined, signature_present
                ) VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s
                )
                """,
                (
                    version_id,
                    tenant_id,
                    artefact_id,
                    version_number,
                    sha256,
                    storage_uri,
                    media_type,
                    title_en,
                    title_fr,
                    principal_id,
                    submitter_role or "unknown",
                    authorized,
                    collected_at,
                    valid_until,
                    quarantined,
                    signature_present,
                ),
            )

        links = metadata.get("lineage") or metadata.get("lineage_links") or []
        if isinstance(links, list):
            for relation, target_uri in lineage_to_rows(links):
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO evidence_lineage (id, tenant_id, evidence_version_id, relation, target_uri)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (uuid7(), tenant_id, version_id, relation, target_uri),
                    )

        audit_append(
            conn,
            tenant_id=tenant_id,
            actor_id=principal_id,
            action="evidence.upload",
            resource_type="evidence_version",
            resource_id=version_id,
            payload={
                "artefact_class": artefact_class,
                "sha256": sha256,
                "authorized_submitter": authorized,
                "quarantined": quarantined,
            },
        )
        return version_id

    @staticmethod
    def can_satisfy_mandatory(
        conn: Connection[Any], *, tenant_id: UUID, evidence_version_id: UUID
    ) -> bool:
        return satisfies_mandatory_spec(
            conn, tenant_id=tenant_id, evidence_version_id=evidence_version_id
        )


def all_artefact_classes() -> list[str]:
    return [ArtefactClass(c).value for c in ArtefactClass]
