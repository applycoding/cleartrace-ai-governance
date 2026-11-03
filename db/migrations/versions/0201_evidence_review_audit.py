"""Package B: evidence store, reviewer workflow, audit extensions."""

from __future__ import annotations

from alembic import op

revision = "0201_evidence_review_audit"
down_revision = "0002_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE evidence_spec (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          artefact_class TEXT NOT NULL,
          required_roles TEXT[] NOT NULL,
          signature_required BOOLEAN NOT NULL DEFAULT false,
          mandatory BOOLEAN NOT NULL DEFAULT false,
          UNIQUE (tenant_id, artefact_class)
        );

        CREATE TABLE evidence_artefact (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          artefact_class TEXT NOT NULL,
          current_version_id UUID,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE evidence_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          evidence_artefact_id UUID NOT NULL REFERENCES evidence_artefact(id),
          version_number INT NOT NULL,
          sha256 TEXT NOT NULL,
          storage_uri TEXT NOT NULL,
          media_type TEXT NOT NULL,
          title_en TEXT NOT NULL,
          title_fr TEXT NOT NULL,
          submitted_by UUID NOT NULL,
          submitter_role_at_time TEXT NOT NULL,
          authorized_submitter BOOLEAN NOT NULL,
          collected_at TIMESTAMPTZ NOT NULL,
          valid_until TIMESTAMPTZ,
          quarantined BOOLEAN NOT NULL DEFAULT false,
          signature_present BOOLEAN NOT NULL DEFAULT false,
          UNIQUE (evidence_artefact_id, version_number)
        );

        CREATE TABLE evidence_lineage (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          evidence_version_id UUID NOT NULL REFERENCES evidence_version(id),
          relation TEXT NOT NULL,
          target_uri TEXT NOT NULL
        );

        CREATE TABLE ai_system_owner (
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          principal_id UUID NOT NULL REFERENCES principal(id),
          PRIMARY KEY (tenant_id, ai_system_id)
        );

        CREATE TABLE finding (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          control_id TEXT NOT NULL,
          current_version_number INT NOT NULL DEFAULT 1,
          etag TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE finding_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          finding_id UUID NOT NULL REFERENCES finding(id),
          version_number INT NOT NULL,
          lifecycle_state TEXT NOT NULL,
          outcome_state TEXT NOT NULL,
          certainty_index NUMERIC(5, 4),
          reason_code TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (finding_id, version_number)
        );

        CREATE TABLE decision_record (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          finding_id UUID NOT NULL REFERENCES finding(id),
          finding_version_number INT NOT NULL,
          review_action TEXT NOT NULL,
          actor_principal_id UUID NOT NULL,
          rationale_en TEXT,
          rationale_fr TEXT,
          reason_code TEXT,
          before_snapshot JSONB,
          after_snapshot JSONB,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE review_exception (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          finding_id UUID NOT NULL REFERENCES finding(id),
          approver_principal_id UUID NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL,
          compensating_controls_en TEXT NOT NULL,
          compensating_controls_fr TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE audit_pii (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          audit_event_id UUID NOT NULL REFERENCES audit_event(id),
          commitment_hash TEXT NOT NULL,
          payload_ciphertext BYTEA NOT NULL
        );

        CREATE TABLE merkle_checkpoint (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          tree_size BIGINT NOT NULL,
          root_hash TEXT NOT NULL,
          signed_tree_head TEXT NOT NULL,
          worm_uri TEXT NOT NULL,
          leaf_manifest_uri TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX idx_evidence_artefact_tenant ON evidence_artefact (tenant_id);
        CREATE INDEX idx_finding_tenant ON finding (tenant_id);
        CREATE INDEX idx_audit_event_tenant_occurred ON audit_event (tenant_id, occurred_at);
        """
    )

    op.execute(
        """
        ALTER TABLE evidence_spec ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_spec FORCE ROW LEVEL SECURITY;
        ALTER TABLE evidence_artefact ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_artefact FORCE ROW LEVEL SECURITY;
        ALTER TABLE evidence_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE evidence_lineage ENABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_lineage FORCE ROW LEVEL SECURITY;
        ALTER TABLE ai_system_owner ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_system_owner FORCE ROW LEVEL SECURITY;
        ALTER TABLE finding ENABLE ROW LEVEL SECURITY;
        ALTER TABLE finding FORCE ROW LEVEL SECURITY;
        ALTER TABLE finding_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE finding_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE decision_record ENABLE ROW LEVEL SECURITY;
        ALTER TABLE decision_record FORCE ROW LEVEL SECURITY;
        ALTER TABLE review_exception ENABLE ROW LEVEL SECURITY;
        ALTER TABLE review_exception FORCE ROW LEVEL SECURITY;
        ALTER TABLE audit_pii ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_pii FORCE ROW LEVEL SECURITY;
        ALTER TABLE merkle_checkpoint ENABLE ROW LEVEL SECURITY;
        ALTER TABLE merkle_checkpoint FORCE ROW LEVEL SECURITY;
        """
    )

    op.execute(
        """
        CREATE POLICY tenant_isolation ON evidence_spec
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON evidence_artefact
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON evidence_version
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON evidence_lineage
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON ai_system_owner
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON finding
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON finding_version
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON decision_record
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON review_exception
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON audit_pii
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON merkle_checkpoint
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        """
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE ON evidence_spec TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON evidence_artefact TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON evidence_version TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON evidence_lineage TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON ai_system_owner TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON finding TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON finding_version TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT ON decision_record TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON review_exception TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT ON audit_pii TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT ON merkle_checkpoint TO cleartrace_app, cleartrace_migrator;

        ALTER TABLE evidence_spec OWNER TO cleartrace_owner;
        ALTER TABLE evidence_artefact OWNER TO cleartrace_owner;
        ALTER TABLE evidence_version OWNER TO cleartrace_owner;
        ALTER TABLE evidence_lineage OWNER TO cleartrace_owner;
        ALTER TABLE ai_system_owner OWNER TO cleartrace_owner;
        ALTER TABLE finding OWNER TO cleartrace_owner;
        ALTER TABLE finding_version OWNER TO cleartrace_owner;
        ALTER TABLE decision_record OWNER TO cleartrace_owner;
        ALTER TABLE review_exception OWNER TO cleartrace_owner;
        ALTER TABLE audit_pii OWNER TO cleartrace_owner;
        ALTER TABLE merkle_checkpoint OWNER TO cleartrace_owner;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS merkle_checkpoint CASCADE;
        DROP TABLE IF EXISTS audit_pii CASCADE;
        DROP TABLE IF EXISTS review_exception CASCADE;
        DROP TABLE IF EXISTS decision_record CASCADE;
        DROP TABLE IF EXISTS finding_version CASCADE;
        DROP TABLE IF EXISTS finding CASCADE;
        DROP TABLE IF EXISTS ai_system_owner CASCADE;
        DROP TABLE IF EXISTS evidence_lineage CASCADE;
        DROP TABLE IF EXISTS evidence_version CASCADE;
        DROP TABLE IF EXISTS evidence_artefact CASCADE;
        DROP TABLE IF EXISTS evidence_spec CASCADE;
        """
    )
