from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from cleartrace_db.session import tenant_transaction
from psycopg import Connection
from uuid6 import uuid7

from cleartrace_core_api.data_policy.crypto import (
    destroy_wrapped_key,
    encrypt_record,
    tombstone_hash,
)
from cleartrace_core_api.data_policy.models import (
    BackupSnapshotView,
    DeletionCertificateStatus,
    DeletionCertificateView,
    DeletionRequestView,
    LegalHoldView,
    RetentionRuleBody,
    TenantDataPolicyView,
)

BACKUP_NOTE_EN = (
    "Backup copies expire on the tenant backup rotation schedule (default 90 days). "
    "Certificates never claim final erasure before key destruction is confirmed."
)
BACKUP_NOTE_FR = (
    "Les copies de sauvegarde expirent selon la rotation des sauvegardes du locataire "
    "(90 jours par défaut). Les certificats ne déclarent jamais l'effacement final avant "
    "la confirmation de destruction des clés."
)

KMS_PENDING_DAYS = 7


class DataPolicyService:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def get_policy(self, tenant_id: UUID) -> TenantDataPolicyView:
        with tenant_transaction(self._dsn, tenant_id) as conn:
            row = self._fetch_policy_row(conn, tenant_id)
            rules = self._fetch_retention_rules(conn, tenant_id)
        return TenantDataPolicyView(
            tenant_id=tenant_id,
            residency_cell_id=row["residency_cell_id"],
            classification_ceiling=row["classification_ceiling"],
            security_profile=row["security_profile"],
            retention_rules=rules,
        )

    def upsert_retention(
        self, tenant_id: UUID, rules: list[RetentionRuleBody]
    ) -> TenantDataPolicyView:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            self._ensure_policy_row(cur, tenant_id)
            for rule in rules:
                cur.execute(
                    """
                    INSERT INTO retention_rule (
                      id, tenant_id, artefact_class,
                      configured_retention_days, statutory_floor_days
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, artefact_class) DO UPDATE SET
                      configured_retention_days = EXCLUDED.configured_retention_days,
                      statutory_floor_days = EXCLUDED.statutory_floor_days
                    """,
                    (
                        uuid7(),
                        tenant_id,
                        rule.artefact_class,
                        rule.configured_retention_days,
                        rule.statutory_floor_days,
                    ),
                )
        return self.get_policy(tenant_id)

    def create_legal_hold(
        self,
        tenant_id: UUID,
        *,
        scope: dict[str, object],
        reason_en: str,
        reason_fr: str,
    ) -> LegalHoldView:
        hold_id = uuid7()
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO legal_hold (
                  id, tenant_id, scope, reason_en, reason_fr, active
                ) VALUES (%s, %s, %s::jsonb, %s, %s, true)
                """,
                (hold_id, tenant_id, json.dumps(scope), reason_en, reason_fr),
            )
        return LegalHoldView(
            id=hold_id,
            scope=scope,
            reason_en=reason_en,
            reason_fr=reason_fr,
            active=True,
            created_at=datetime.now(tz=UTC),
        )

    def store_encrypted_payload(
        self,
        tenant_id: UUID,
        *,
        artefact_class: str,
        plaintext: bytes,
        last_used_at: datetime,
    ) -> UUID:
        blob = encrypt_record(plaintext)
        payload_id = uuid7()
        key_id = uuid7()
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO encrypted_payload (
                  id, tenant_id, artefact_class, content_hash,
                  ciphertext, data_key_id, last_used_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload_id,
                    tenant_id,
                    artefact_class,
                    blob.content_hash,
                    blob.ciphertext,
                    key_id,
                    last_used_at,
                ),
            )
            cur.execute(
                """
                INSERT INTO record_data_key (id, tenant_id, payload_id, wrapped_key)
                VALUES (%s, %s, %s, %s)
                """,
                (key_id, tenant_id, payload_id, blob.wrapped_key),
            )
        return payload_id

    def deletion_blocked_reason(
        self,
        conn: Connection[Any],
        tenant_id: UUID,
        payload_id: UUID,
        *,
        as_of: datetime,
    ) -> str | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT deleted_at FROM encrypted_payload
                WHERE id = %s AND tenant_id = %s
                """,
                (payload_id, tenant_id),
            )
            row = cur.fetchone()
            if row is None:
                return "not_found"
            if row[0] is not None:
                return "already_deleted"
            cur.execute(
                """
                SELECT 1 FROM legal_hold
                WHERE tenant_id = %s AND active = true
                  AND (scope->>'payload_id' IS NULL OR scope->>'payload_id' = %s)
                LIMIT 1
                """,
                (tenant_id, str(payload_id)),
            )
            if cur.fetchone():
                return "legal_hold"
            cur.execute(
                """
                SELECT ep.last_used_at, rr.configured_retention_days, rr.statutory_floor_days
                FROM encrypted_payload ep
                LEFT JOIN retention_rule rr
                  ON rr.tenant_id = ep.tenant_id AND rr.artefact_class = ep.artefact_class
                WHERE ep.id = %s AND ep.tenant_id = %s
                """,
                (payload_id, tenant_id),
            )
            retention_row = cur.fetchone()
            if retention_row is None:
                return "not_found"
            last_used, configured_days, floor_days = retention_row
            configured_days = configured_days or 365
            floor_days = floor_days or 730
            effective_days = max(configured_days, floor_days)
            delete_after = last_used + timedelta(days=effective_days)
            if as_of < delete_after:
                return "retention"
        return None

    def request_deletion(self, tenant_id: UUID, payload_ids: list[UUID]) -> DeletionRequestView:
        request_id = uuid7()
        now = datetime.now(tz=UTC)
        blocked: list[str] = []
        with tenant_transaction(self._dsn, tenant_id) as conn:
            for pid in payload_ids:
                reason = self.deletion_blocked_reason(conn, tenant_id, pid, as_of=now)
                if reason:
                    blocked.append(f"{pid}:{reason}")
            if blocked:
                raise ValueError(f"deletion blocked: {', '.join(blocked)}")
            cert_id = uuid7()
            scheduled = now + timedelta(days=KMS_PENDING_DAYS)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO deletion_request (id, tenant_id, payload_ids, status)
                    VALUES (%s, %s, %s, 'completed')
                    """,
                    (request_id, tenant_id, payload_ids),
                )
                for pid in payload_ids:
                    cur.execute(
                        """
                        SELECT k.id, k.wrapped_key, p.content_hash
                        FROM record_data_key k
                        JOIN encrypted_payload p ON p.id = k.payload_id
                        WHERE k.payload_id = %s AND k.tenant_id = %s
                        """,
                        (pid, tenant_id),
                    )
                    key_row = cur.fetchone()
                    if key_row is None:
                        raise ValueError(f"missing key for {pid}")
                    key_id, wrapped_key, content_hash = key_row
                    destroyed = destroy_wrapped_key(bytes(wrapped_key))
                    cur.execute(
                        """
                        UPDATE record_data_key
                        SET wrapped_key = %s,
                            destroyed_at = %s,
                            kms_pending_until = %s
                        WHERE id = %s
                        """,
                        (destroyed, now, scheduled, key_id),
                    )
                    ts_hash = tombstone_hash(content_hash, str(pid))
                    cur.execute(
                        """
                        UPDATE encrypted_payload
                        SET ciphertext = %s,
                            deleted_at = %s,
                            tombstone_hash = %s
                        WHERE id = %s AND tenant_id = %s
                        """,
                        (b"", now, ts_hash, pid, tenant_id),
                    )
                cur.execute(
                    """
                    INSERT INTO deletion_certificate (
                      id, tenant_id, deletion_request_id, status,
                      key_destruction_scheduled_at, key_destroyed_at,
                      backup_expiry_note_en, backup_expiry_note_fr
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cert_id,
                        tenant_id,
                        request_id,
                        DeletionCertificateStatus.PENDING.value,
                        scheduled,
                        now,
                        BACKUP_NOTE_EN,
                        BACKUP_NOTE_FR,
                    ),
                )
                cur.execute(
                    """
                    UPDATE deletion_request
                    SET completed_at = %s
                    WHERE id = %s
                    """,
                    (now, request_id),
                )
        return DeletionRequestView(
            id=request_id,
            payload_ids=payload_ids,
            status="completed",
            certificate_id=cert_id,
            requested_at=now,
            completed_at=now,
        )

    def finalize_due_certificates(self, tenant_id: UUID) -> list[DeletionCertificateView]:
        now = datetime.now(tz=UTC)
        finalized: list[DeletionCertificateView] = []
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, deletion_request_id, key_destruction_scheduled_at,
                       key_destroyed_at, issued_at
                FROM deletion_certificate
                WHERE tenant_id = %s AND status = %s
                  AND key_destruction_scheduled_at <= %s
                """,
                (tenant_id, DeletionCertificateStatus.PENDING.value, now),
            )
            rows = cur.fetchall()
            for row in rows:
                cert_id, req_id, scheduled, destroyed, issued = row
                cur.execute(
                    """
                    UPDATE deletion_certificate
                    SET status = %s, finalized_at = %s
                    WHERE id = %s
                    """,
                    (DeletionCertificateStatus.FINAL.value, now, cert_id),
                )
                finalized.append(
                    DeletionCertificateView(
                        id=cert_id,
                        deletion_request_id=req_id,
                        status=DeletionCertificateStatus.FINAL,
                        key_destruction_scheduled_at=scheduled,
                        key_destroyed_at=destroyed,
                        backup_expiry_note_en=BACKUP_NOTE_EN,
                        backup_expiry_note_fr=BACKUP_NOTE_FR,
                        issued_at=issued,
                        finalized_at=now,
                    )
                )
        return finalized

    def get_certificate(
        self, tenant_id: UUID, certificate_id: UUID
    ) -> DeletionCertificateView | None:
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, deletion_request_id, status, key_destruction_scheduled_at,
                       key_destroyed_at, backup_expiry_note_en, backup_expiry_note_fr,
                       issued_at, finalized_at
                FROM deletion_certificate
                WHERE id = %s AND tenant_id = %s
                """,
                (certificate_id, tenant_id),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return DeletionCertificateView(
            id=row[0],
            deletion_request_id=row[1],
            status=DeletionCertificateStatus(row[2]),
            key_destruction_scheduled_at=row[3],
            key_destroyed_at=row[4],
            backup_expiry_note_en=row[5],
            backup_expiry_note_fr=row[6],
            issued_at=row[7],
            finalized_at=row[8],
        )

    def create_backup_snapshot(self, tenant_id: UUID, *, label: str) -> BackupSnapshotView:
        snapshot_id = uuid7()
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content_hash, artefact_class, ciphertext, deleted_at
                FROM encrypted_payload
                WHERE tenant_id = %s
                ORDER BY id
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
            manifest_rows = [
                {
                    "id": str(r[0]),
                    "content_hash": r[1],
                    "artefact_class": r[2],
                    "ciphertext_sha256": hashlib.sha256(bytes(r[3])).hexdigest(),
                    "deleted_at": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]
            manifest_bytes = json.dumps(manifest_rows, sort_keys=True).encode()
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            cur.execute(
                """
                INSERT INTO data_policy_backup_snapshot (
                  id, tenant_id, snapshot_label, manifest_sha256,
                  payload_count, manifest
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    snapshot_id,
                    tenant_id,
                    label,
                    manifest_sha,
                    len(manifest_rows),
                    manifest_bytes.decode(),
                ),
            )
        return BackupSnapshotView(
            id=snapshot_id,
            snapshot_label=label,
            manifest_sha256=manifest_sha,
            payload_count=len(manifest_rows),
            created_at=datetime.now(tz=UTC),
        )

    def verify_backup_checksums(self, tenant_id: UUID, snapshot_id: UUID) -> tuple[int, int]:
        """Return (matched, total) payload checksum entries."""
        with tenant_transaction(self._dsn, tenant_id) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT manifest FROM data_policy_backup_snapshot
                WHERE id = %s AND tenant_id = %s
                """,
                (snapshot_id, tenant_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("snapshot not found")
            manifest = row[0]
            matched = 0
            total = len(manifest)
            for entry in manifest:
                pid = UUID(entry["id"])
                cur.execute(
                    """
                    SELECT content_hash, ciphertext, deleted_at
                    FROM encrypted_payload WHERE id = %s AND tenant_id = %s
                    """,
                    (pid, tenant_id),
                )
                live = cur.fetchone()
                if live is None:
                    continue
                content_hash, ciphertext, deleted_at = live
                if content_hash != entry["content_hash"]:
                    continue
                cipher_sha = hashlib.sha256(bytes(ciphertext)).hexdigest()
                if cipher_sha != entry["ciphertext_sha256"]:
                    continue
                deleted_iso = deleted_at.isoformat() if deleted_at else None
                if deleted_iso != entry["deleted_at"]:
                    continue
                matched += 1
        return matched, total

    def _ensure_policy_row(self, cur: Any, tenant_id: UUID) -> None:
        cur.execute(
            """
            INSERT INTO tenant_data_policy (tenant_id)
            VALUES (%s)
            ON CONFLICT (tenant_id) DO NOTHING
            """,
            (tenant_id,),
        )

    def _fetch_policy_row(self, conn: Connection[Any], tenant_id: UUID) -> dict[str, Any]:
        with conn.cursor() as cur:
            self._ensure_policy_row(cur, tenant_id)
            cur.execute(
                """
                SELECT residency_cell_id, classification_ceiling, security_profile
                FROM tenant_data_policy WHERE tenant_id = %s
                """,
                (tenant_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("policy row missing after insert")
        return {
            "residency_cell_id": row[0],
            "classification_ceiling": row[1],
            "security_profile": row[2],
        }

    def _fetch_retention_rules(
        self, conn: Connection[Any], tenant_id: UUID
    ) -> list[RetentionRuleBody]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT artefact_class, configured_retention_days, statutory_floor_days
                FROM retention_rule WHERE tenant_id = %s ORDER BY artefact_class
                """,
                (tenant_id,),
            )
            rows = cur.fetchall()
        # Stored rows are trusted output, so build them without re-applying the
        # request-side validators (model_construct skips validation).
        return [
            RetentionRuleBody.model_construct(
                artefact_class=r[0],
                configured_retention_days=r[1],
                statutory_floor_days=r[2],
            )
            for r in rows
        ]
