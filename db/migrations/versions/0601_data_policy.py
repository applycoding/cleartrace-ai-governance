"""Package F: retention, legal hold, encrypted records, deletion certificates."""

from __future__ import annotations

from alembic import op

revision = "0601_data_policy"
down_revision = "0002_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tenant_data_policy (
          tenant_id UUID PRIMARY KEY REFERENCES tenant(id),
          residency_cell_id UUID REFERENCES cell(id),
          classification_ceiling TEXT NOT NULL DEFAULT 'unclassified',
          security_profile TEXT NOT NULL DEFAULT 'default',
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE retention_rule (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          artefact_class TEXT NOT NULL,
          configured_retention_days INT NOT NULL,
          statutory_floor_days INT NOT NULL DEFAULT 730,
          UNIQUE (tenant_id, artefact_class)
        );

        CREATE TABLE legal_hold (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          scope JSONB NOT NULL,
          reason_en TEXT NOT NULL,
          reason_fr TEXT NOT NULL,
          active BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          released_at TIMESTAMPTZ
        );

        CREATE TABLE encrypted_payload (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          artefact_class TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          ciphertext BYTEA NOT NULL,
          data_key_id UUID NOT NULL,
          last_used_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          deleted_at TIMESTAMPTZ,
          tombstone_hash TEXT
        );

        CREATE TABLE record_data_key (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          payload_id UUID NOT NULL REFERENCES encrypted_payload(id),
          wrapped_key BYTEA NOT NULL,
          destroyed_at TIMESTAMPTZ,
          kms_pending_until TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE deletion_request (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          payload_ids UUID[] NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          completed_at TIMESTAMPTZ
        );

        CREATE TABLE deletion_certificate (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          deletion_request_id UUID NOT NULL REFERENCES deletion_request(id),
          status TEXT NOT NULL,
          key_destruction_scheduled_at TIMESTAMPTZ,
          key_destroyed_at TIMESTAMPTZ,
          backup_expiry_note_en TEXT NOT NULL,
          backup_expiry_note_fr TEXT NOT NULL,
          issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          finalized_at TIMESTAMPTZ
        );

        CREATE TABLE data_policy_backup_snapshot (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          snapshot_label TEXT NOT NULL,
          manifest_sha256 TEXT NOT NULL,
          payload_count INT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          manifest JSONB NOT NULL
        );

        ALTER TABLE tenant_data_policy ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tenant_data_policy FORCE ROW LEVEL SECURITY;
        ALTER TABLE retention_rule ENABLE ROW LEVEL SECURITY;
        ALTER TABLE retention_rule FORCE ROW LEVEL SECURITY;
        ALTER TABLE legal_hold ENABLE ROW LEVEL SECURITY;
        ALTER TABLE legal_hold FORCE ROW LEVEL SECURITY;
        ALTER TABLE encrypted_payload ENABLE ROW LEVEL SECURITY;
        ALTER TABLE encrypted_payload FORCE ROW LEVEL SECURITY;
        ALTER TABLE record_data_key ENABLE ROW LEVEL SECURITY;
        ALTER TABLE record_data_key FORCE ROW LEVEL SECURITY;
        ALTER TABLE deletion_request ENABLE ROW LEVEL SECURITY;
        ALTER TABLE deletion_request FORCE ROW LEVEL SECURITY;
        ALTER TABLE deletion_certificate ENABLE ROW LEVEL SECURITY;
        ALTER TABLE deletion_certificate FORCE ROW LEVEL SECURITY;
        ALTER TABLE data_policy_backup_snapshot ENABLE ROW LEVEL SECURITY;
        ALTER TABLE data_policy_backup_snapshot FORCE ROW LEVEL SECURITY;

        CREATE POLICY tenant_isolation ON tenant_data_policy
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON retention_rule
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON legal_hold
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON encrypted_payload
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON record_data_key
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON deletion_request
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON deletion_certificate
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON data_policy_backup_snapshot
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

        GRANT SELECT, INSERT, UPDATE ON tenant_data_policy TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON retention_rule TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON legal_hold TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON encrypted_payload TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON record_data_key TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON deletion_request TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON deletion_certificate TO cleartrace_app;
        GRANT SELECT, INSERT, UPDATE ON data_policy_backup_snapshot TO cleartrace_app;

        ALTER TABLE tenant_data_policy OWNER TO cleartrace_owner;
        ALTER TABLE retention_rule OWNER TO cleartrace_owner;
        ALTER TABLE legal_hold OWNER TO cleartrace_owner;
        ALTER TABLE encrypted_payload OWNER TO cleartrace_owner;
        ALTER TABLE record_data_key OWNER TO cleartrace_owner;
        ALTER TABLE deletion_request OWNER TO cleartrace_owner;
        ALTER TABLE deletion_certificate OWNER TO cleartrace_owner;
        ALTER TABLE data_policy_backup_snapshot OWNER TO cleartrace_owner;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS data_policy_backup_snapshot CASCADE;
        DROP TABLE IF EXISTS deletion_certificate CASCADE;
        DROP TABLE IF EXISTS deletion_request CASCADE;
        DROP TABLE IF EXISTS record_data_key CASCADE;
        DROP TABLE IF EXISTS encrypted_payload CASCADE;
        DROP TABLE IF EXISTS legal_hold CASCADE;
        DROP TABLE IF EXISTS retention_rule CASCADE;
        DROP TABLE IF EXISTS tenant_data_policy CASCADE;
        """
    )
