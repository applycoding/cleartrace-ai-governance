"""Initial ClearTrace schema: tenancy, RLS, bitemporal, audit, outbox."""

from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE EXTENSION IF NOT EXISTS vector;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          CREATE EXTENSION IF NOT EXISTS pgaudit;
        EXCEPTION
          WHEN OTHERS THEN
            RAISE NOTICE 'pgaudit extension unavailable: %', SQLERRM;
        END $$;
        """
    )

    op.execute(
        """
        CREATE ROLE cleartrace_app NOLOGIN NOBYPASSRLS;
        CREATE ROLE cleartrace_migrator NOLOGIN;
        CREATE ROLE cleartrace_owner NOLOGIN;
        """
    )

    op.execute(
        """
        CREATE TABLE cell (
          id UUID PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          jurisdiction TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE tenant (
          id UUID PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE tenant_cell_binding (
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          cell_id UUID NOT NULL REFERENCES cell(id),
          bound_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (tenant_id)
        );

        CREATE TABLE org_unit (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          code TEXT NOT NULL,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          UNIQUE (tenant_id, code)
        );

        CREATE TABLE app_role (
          id UUID PRIMARY KEY,
          code TEXT NOT NULL UNIQUE,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL
        );

        CREATE TABLE principal (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          external_id TEXT NOT NULL,
          email TEXT NOT NULL,
          display_name TEXT NOT NULL,
          UNIQUE (tenant_id, external_id)
        );

        CREATE TABLE role_assignment (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          principal_id UUID NOT NULL REFERENCES principal(id),
          role_code TEXT NOT NULL REFERENCES app_role(code),
          valid_from TIMESTAMPTZ NOT NULL,
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          superseded_at TIMESTAMPTZ
        );

        CREATE TABLE ai_system (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          system_key TEXT NOT NULL,
          UNIQUE (tenant_id, system_key)
        );

        CREATE TABLE ai_system_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          description_en TEXT NOT NULL,
          description_fr TEXT NOT NULL,
          valid_from TIMESTAMPTZ NOT NULL,
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          superseded_at TIMESTAMPTZ
        );

        CREATE TABLE audit_event (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          actor_id UUID,
          action TEXT NOT NULL,
          resource_type TEXT NOT NULL,
          resource_id UUID,
          prev_hash TEXT NOT NULL,
          event_hash TEXT NOT NULL,
          payload JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE TABLE outbox (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          subject TEXT NOT NULL,
          payload JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          published_at TIMESTAMPTZ,
          message_id TEXT NOT NULL UNIQUE
        );

        CREATE TABLE processed_event_ids (
          message_id TEXT PRIMARY KEY,
          processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        ALTER TABLE org_unit ENABLE ROW LEVEL SECURITY;
        ALTER TABLE org_unit FORCE ROW LEVEL SECURITY;
        ALTER TABLE principal ENABLE ROW LEVEL SECURITY;
        ALTER TABLE principal FORCE ROW LEVEL SECURITY;
        ALTER TABLE role_assignment ENABLE ROW LEVEL SECURITY;
        ALTER TABLE role_assignment FORCE ROW LEVEL SECURITY;
        ALTER TABLE ai_system ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_system FORCE ROW LEVEL SECURITY;
        ALTER TABLE ai_system_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_system_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE audit_event ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_event FORCE ROW LEVEL SECURITY;
        ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
        ALTER TABLE outbox FORCE ROW LEVEL SECURITY;
        """
    )

    op.execute(
        """
        CREATE POLICY tenant_isolation ON org_unit
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON principal
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON role_assignment
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON ai_system
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON ai_system_version
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON audit_event
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON outbox
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleartrace_close_and_insert_system_version(
          p_tenant_id UUID,
          p_system_id UUID,
          p_name_en TEXT,
          p_name_fr TEXT,
          p_description_en TEXT,
          p_description_fr TEXT,
          p_valid_from TIMESTAMPTZ,
          p_new_id UUID
        ) RETURNS UUID
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
          PERFORM set_config('app.tenant_id', p_tenant_id::text, true);
          UPDATE ai_system_version
            SET valid_to = p_valid_from,
                superseded_at = now()
          WHERE ai_system_id = p_system_id
            AND tenant_id = p_tenant_id
            AND superseded_at IS NULL
            AND valid_to IS NULL;
          INSERT INTO ai_system_version (
            id, tenant_id, ai_system_id,
            name_en, name_fr, description_en, description_fr,
            valid_from, valid_to, recorded_at, superseded_at
          ) VALUES (
            p_new_id, p_tenant_id, p_system_id,
            p_name_en, p_name_fr, p_description_en, p_description_fr,
            p_valid_from, NULL, now(), NULL
          );
          RETURN p_new_id;
        END;
        $$;

        REVOKE ALL ON FUNCTION cleartrace_close_and_insert_system_version FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION cleartrace_close_and_insert_system_version TO cleartrace_app;
        """
    )

    op.execute(
        """
        GRANT USAGE ON SCHEMA public TO cleartrace_app, cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cleartrace_migrator;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cleartrace_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cleartrace_app, cleartrace_migrator;

        REVOKE UPDATE, DELETE ON role_assignment FROM cleartrace_app;
        REVOKE UPDATE, DELETE ON ai_system_version FROM cleartrace_app;

        ALTER TABLE tenant OWNER TO cleartrace_owner;
        ALTER TABLE cell OWNER TO cleartrace_owner;
        ALTER TABLE tenant_cell_binding OWNER TO cleartrace_owner;
        ALTER TABLE org_unit OWNER TO cleartrace_owner;
        ALTER TABLE app_role OWNER TO cleartrace_owner;
        ALTER TABLE principal OWNER TO cleartrace_owner;
        ALTER TABLE role_assignment OWNER TO cleartrace_owner;
        ALTER TABLE ai_system OWNER TO cleartrace_owner;
        ALTER TABLE ai_system_version OWNER TO cleartrace_owner;
        ALTER TABLE audit_event OWNER TO cleartrace_owner;
        ALTER TABLE outbox OWNER TO cleartrace_owner;
        ALTER TABLE processed_event_ids OWNER TO cleartrace_owner;

        GRANT cleartrace_owner TO cleartrace_migrator;
        ALTER ROLE cleartrace_app WITH LOGIN PASSWORD 'cleartrace_app';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM cleartrace_app, cleartrace_migrator;
        REVOKE ALL ON SCHEMA public FROM cleartrace_app, cleartrace_migrator;
        REASSIGN OWNED BY cleartrace_app TO cleartrace_owner;
        REASSIGN OWNED BY cleartrace_migrator TO cleartrace_owner;
        DROP OWNED BY cleartrace_app;
        DROP OWNED BY cleartrace_migrator;
        DROP FUNCTION IF EXISTS cleartrace_close_and_insert_system_version;
        DROP TABLE IF EXISTS processed_event_ids CASCADE;
        DROP TABLE IF EXISTS outbox CASCADE;
        DROP TABLE IF EXISTS audit_event CASCADE;
        DROP TABLE IF EXISTS ai_system_version CASCADE;
        DROP TABLE IF EXISTS ai_system CASCADE;
        DROP TABLE IF EXISTS role_assignment CASCADE;
        DROP TABLE IF EXISTS principal CASCADE;
        DROP TABLE IF EXISTS app_role CASCADE;
        DROP TABLE IF EXISTS org_unit CASCADE;
        DROP TABLE IF EXISTS tenant_cell_binding CASCADE;
        DROP TABLE IF EXISTS tenant CASCADE;
        DROP TABLE IF EXISTS cell CASCADE;
        DROP ROLE IF EXISTS cleartrace_app;
        DROP ROLE IF EXISTS cleartrace_migrator;
        DROP ROLE IF EXISTS cleartrace_owner;
        """
    )
