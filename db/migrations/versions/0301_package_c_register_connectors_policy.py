"""Package C: register categories, precedence, connectors, policy watcher."""

from __future__ import annotations

from alembic import op

revision = "0301_package_c"
down_revision = "0002_seed_reference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE system_group (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          code TEXT NOT NULL,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          UNIQUE (tenant_id, code)
        );

        CREATE TABLE system_group_member (
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          group_id UUID NOT NULL REFERENCES system_group(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          PRIMARY KEY (group_id, ai_system_id)
        );

        CREATE TABLE register_category_value (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          category_number SMALLINT NOT NULL CHECK (category_number BETWEEN 1 AND 15),
          slot_key TEXT NOT NULL,
          value_en TEXT,
          value_fr TEXT,
          needs_intake BOOLEAN NOT NULL DEFAULT false,
          source_id TEXT NOT NULL,
          source_tier SMALLINT NOT NULL CHECK (source_tier BETWEEN 1 AND 3),
          event_time TIMESTAMPTZ NOT NULL,
          valid_from TIMESTAMPTZ NOT NULL,
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, ai_system_id, category_number, slot_key, valid_to)
        );

        CREATE TABLE source_record (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          source_id TEXT NOT NULL,
          connector_instance_id UUID,
          payload JSONB NOT NULL,
          received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          event_time TIMESTAMPTZ NOT NULL
        );

        CREATE TABLE field_provenance (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          register_value_id UUID NOT NULL REFERENCES register_category_value(id),
          source_record_id UUID NOT NULL REFERENCES source_record(id),
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE quarantine_item (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          field_path TEXT NOT NULL,
          reason TEXT NOT NULL,
          source_record_id UUID REFERENCES source_record(id),
          payload JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          resolved_at TIMESTAMPTZ
        );

        CREATE TABLE connector_instance (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          name TEXT NOT NULL,
          manifest JSONB NOT NULL,
          enabled BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, name)
        );

        CREATE TABLE connector_run (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          connector_instance_id UUID NOT NULL REFERENCES connector_instance(id),
          started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          finished_at TIMESTAMPTZ,
          status TEXT NOT NULL,
          records_ingested INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE policy_source (
          id UUID PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          canonical_url_en TEXT NOT NULL,
          canonical_url_fr TEXT NOT NULL
        );

        CREATE TABLE policy_snapshot (
          id UUID PRIMARY KEY,
          policy_source_id UUID NOT NULL REFERENCES policy_source(id),
          locale TEXT NOT NULL CHECK (locale IN ('en', 'fr')),
          raw_content TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          is_active BOOLEAN NOT NULL DEFAULT false
        );

        CREATE TABLE policy_diff (
          id UUID PRIMARY KEY,
          policy_source_id UUID NOT NULL REFERENCES policy_source(id),
          from_snapshot_id UUID NOT NULL REFERENCES policy_snapshot(id),
          to_snapshot_id UUID NOT NULL REFERENCES policy_snapshot(id),
          substantive BOOLEAN NOT NULL,
          formatting_only BOOLEAN NOT NULL,
          clause_changes JSONB NOT NULL,
          steward_approved BOOLEAN NOT NULL DEFAULT false,
          activated BOOLEAN NOT NULL DEFAULT false,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE impact_set (
          id UUID PRIMARY KEY,
          policy_diff_id UUID NOT NULL REFERENCES policy_diff(id),
          affected_system_ids UUID[] NOT NULL,
          affected_control_ids TEXT[] NOT NULL,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE reassessment_flag (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          control_id TEXT NOT NULL,
          reason TEXT NOT NULL,
          policy_diff_id UUID REFERENCES policy_diff(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          cleared_at TIMESTAMPTZ
        );

        CREATE TABLE egress_destination_profile (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          connector_instance_id UUID NOT NULL REFERENCES connector_instance(id),
          host TEXT NOT NULL,
          port INTEGER NOT NULL,
          cidr TEXT,
          mtls_required BOOLEAN NOT NULL DEFAULT false
        );
        """
    )

    op.execute(
        """
        ALTER TABLE system_group ENABLE ROW LEVEL SECURITY;
        ALTER TABLE system_group FORCE ROW LEVEL SECURITY;
        ALTER TABLE system_group_member ENABLE ROW LEVEL SECURITY;
        ALTER TABLE system_group_member FORCE ROW LEVEL SECURITY;
        ALTER TABLE register_category_value ENABLE ROW LEVEL SECURITY;
        ALTER TABLE register_category_value FORCE ROW LEVEL SECURITY;
        ALTER TABLE source_record ENABLE ROW LEVEL SECURITY;
        ALTER TABLE source_record FORCE ROW LEVEL SECURITY;
        ALTER TABLE field_provenance ENABLE ROW LEVEL SECURITY;
        ALTER TABLE field_provenance FORCE ROW LEVEL SECURITY;
        ALTER TABLE quarantine_item ENABLE ROW LEVEL SECURITY;
        ALTER TABLE quarantine_item FORCE ROW LEVEL SECURITY;
        ALTER TABLE connector_instance ENABLE ROW LEVEL SECURITY;
        ALTER TABLE connector_instance FORCE ROW LEVEL SECURITY;
        ALTER TABLE connector_run ENABLE ROW LEVEL SECURITY;
        ALTER TABLE connector_run FORCE ROW LEVEL SECURITY;
        ALTER TABLE egress_destination_profile ENABLE ROW LEVEL SECURITY;
        ALTER TABLE egress_destination_profile FORCE ROW LEVEL SECURITY;
        ALTER TABLE reassessment_flag ENABLE ROW LEVEL SECURITY;
        ALTER TABLE reassessment_flag FORCE ROW LEVEL SECURITY;

        CREATE POLICY tenant_isolation ON system_group
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON system_group_member
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON register_category_value
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON source_record
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON field_provenance
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON quarantine_item
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON connector_instance
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON connector_run
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON egress_destination_profile
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON reassessment_flag
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

        ALTER TABLE system_group OWNER TO cleartrace_owner;
        ALTER TABLE system_group_member OWNER TO cleartrace_owner;
        ALTER TABLE register_category_value OWNER TO cleartrace_owner;
        ALTER TABLE source_record OWNER TO cleartrace_owner;
        ALTER TABLE field_provenance OWNER TO cleartrace_owner;
        ALTER TABLE quarantine_item OWNER TO cleartrace_owner;
        ALTER TABLE connector_instance OWNER TO cleartrace_owner;
        ALTER TABLE connector_run OWNER TO cleartrace_owner;
        ALTER TABLE policy_source OWNER TO cleartrace_owner;
        ALTER TABLE policy_snapshot OWNER TO cleartrace_owner;
        ALTER TABLE policy_diff OWNER TO cleartrace_owner;
        ALTER TABLE impact_set OWNER TO cleartrace_owner;
        ALTER TABLE reassessment_flag OWNER TO cleartrace_owner;
        ALTER TABLE egress_destination_profile OWNER TO cleartrace_owner;

        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cleartrace_app, cleartrace_migrator;
        REVOKE UPDATE, DELETE ON register_category_value FROM cleartrace_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS egress_destination_profile CASCADE;
        DROP TABLE IF EXISTS reassessment_flag CASCADE;
        DROP TABLE IF EXISTS impact_set CASCADE;
        DROP TABLE IF EXISTS policy_diff CASCADE;
        DROP TABLE IF EXISTS policy_snapshot CASCADE;
        DROP TABLE IF EXISTS policy_source CASCADE;
        DROP TABLE IF EXISTS connector_run CASCADE;
        DROP TABLE IF EXISTS connector_instance CASCADE;
        DROP TABLE IF EXISTS quarantine_item CASCADE;
        DROP TABLE IF EXISTS field_provenance CASCADE;
        DROP TABLE IF EXISTS source_record CASCADE;
        DROP TABLE IF EXISTS register_category_value CASCADE;
        DROP TABLE IF EXISTS system_group_member CASCADE;
        DROP TABLE IF EXISTS system_group CASCADE;
        """
    )
