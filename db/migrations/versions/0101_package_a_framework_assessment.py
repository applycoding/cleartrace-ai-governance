"""Package A: framework studio tables, assignments, assessment findings."""

from __future__ import annotations

from alembic import op

revision = "0101_package_a"
down_revision = "0002_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE framework (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          slug TEXT NOT NULL,
          owner TEXT NOT NULL,
          obligation_type TEXT NOT NULL,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          source_url_en TEXT NOT NULL,
          source_url_fr TEXT NOT NULL,
          UNIQUE (tenant_id, slug)
        );

        CREATE TABLE framework_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          framework_id UUID NOT NULL REFERENCES framework(id),
          semver TEXT NOT NULL,
          lifecycle TEXT NOT NULL,
          effective_from TIMESTAMPTZ,
          effective_to TIMESTAMPTZ,
          source_hash_en TEXT,
          source_hash_fr TEXT,
          valid_from TIMESTAMPTZ NOT NULL,
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          superseded_at TIMESTAMPTZ,
          UNIQUE (framework_id, semver)
        );

        CREATE TABLE clause (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          framework_version_id UUID NOT NULL REFERENCES framework_version(id),
          clause_ref TEXT NOT NULL,
          text_en TEXT NOT NULL,
          text_fr TEXT NOT NULL,
          UNIQUE (framework_version_id, clause_ref)
        );

        CREATE TABLE control (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          framework_id UUID NOT NULL REFERENCES framework(id),
          control_key TEXT NOT NULL,
          UNIQUE (tenant_id, control_key)
        );

        CREATE TABLE control_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          control_id UUID NOT NULL REFERENCES control(id),
          framework_version_id UUID NOT NULL REFERENCES framework_version(id),
          clause_id UUID REFERENCES clause(id),
          semver TEXT NOT NULL,
          title_en TEXT NOT NULL,
          title_fr TEXT NOT NULL,
          obligation_type TEXT NOT NULL,
          applicability_expr TEXT,
          rule_ref TEXT,
          remediation_en TEXT NOT NULL,
          remediation_fr TEXT NOT NULL,
          valid_from TIMESTAMPTZ NOT NULL,
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          superseded_at TIMESTAMPTZ
        );

        CREATE TABLE objective (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          control_version_id UUID NOT NULL REFERENCES control_version(id),
          objective_key TEXT NOT NULL,
          description_en TEXT NOT NULL,
          description_fr TEXT NOT NULL,
          critical_gate BOOLEAN NOT NULL DEFAULT false,
          evidence_specs JSONB NOT NULL DEFAULT '[]'::jsonb,
          rule_ref TEXT,
          UNIQUE (control_version_id, objective_key)
        );

        CREATE TABLE crosswalk (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          source_control_version_id UUID NOT NULL REFERENCES control_version(id),
          target_control_version_id UUID NOT NULL REFERENCES control_version(id),
          relation TEXT NOT NULL,
          reviewer TEXT NOT NULL,
          source_note TEXT NOT NULL
        );

        CREATE TABLE system_group (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          slug TEXT NOT NULL,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          criteria JSONB NOT NULL DEFAULT '{}'::jsonb,
          UNIQUE (tenant_id, slug)
        );

        CREATE TABLE system_group_member (
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          group_id UUID NOT NULL REFERENCES system_group(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          PRIMARY KEY (group_id, ai_system_id)
        );

        CREATE TABLE assignment (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          framework_version_id UUID NOT NULL REFERENCES framework_version(id),
          ai_system_id UUID REFERENCES ai_system(id),
          group_id UUID REFERENCES system_group(id),
          criteria_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
          approved_by TEXT,
          valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
          valid_to TIMESTAMPTZ,
          CHECK (
            (ai_system_id IS NOT NULL AND group_id IS NULL)
            OR (ai_system_id IS NULL AND group_id IS NOT NULL)
          )
        );

        CREATE TABLE reassessment_flag (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          framework_version_id UUID REFERENCES framework_version(id),
          control_version_id UUID REFERENCES control_version(id),
          reason TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          cleared_at TIMESTAMPTZ
        );

        CREATE TABLE assessment_run (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          framework_version_id UUID NOT NULL REFERENCES framework_version(id),
          status TEXT NOT NULL,
          engine_bundle_digest TEXT NOT NULL,
          started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          completed_at TIMESTAMPTZ
        );

        CREATE TABLE finding (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          assessment_run_id UUID NOT NULL REFERENCES assessment_run(id),
          control_version_id UUID NOT NULL REFERENCES control_version(id),
          outcome_state TEXT NOT NULL,
          reason_code TEXT NOT NULL,
          certainty_index NUMERIC(4, 3) NOT NULL,
          lifecycle_state TEXT NOT NULL DEFAULT 'DRAFT_AUTO',
          engine_bundle_digest TEXT NOT NULL
        );

        CREATE TABLE finding_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          finding_id UUID NOT NULL REFERENCES finding(id),
          explanation_en TEXT NOT NULL,
          explanation_fr TEXT NOT NULL,
          valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          superseded_at TIMESTAMPTZ
        );
        """
    )

    for table in (
        "framework",
        "framework_version",
        "clause",
        "control",
        "control_version",
        "objective",
        "crosswalk",
        "system_group",
        "system_group_member",
        "assignment",
        "reassessment_flag",
        "assessment_run",
        "finding",
        "finding_version",
    ):
        op.execute(
            f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON {table}
              USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
            """
        )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cleartrace_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS finding_version CASCADE;
        DROP TABLE IF EXISTS finding CASCADE;
        DROP TABLE IF EXISTS assessment_run CASCADE;
        DROP TABLE IF EXISTS reassessment_flag CASCADE;
        DROP TABLE IF EXISTS assignment CASCADE;
        DROP TABLE IF EXISTS system_group_member CASCADE;
        DROP TABLE IF EXISTS system_group CASCADE;
        DROP TABLE IF EXISTS crosswalk CASCADE;
        DROP TABLE IF EXISTS objective CASCADE;
        DROP TABLE IF EXISTS control_version CASCADE;
        DROP TABLE IF EXISTS control CASCADE;
        DROP TABLE IF EXISTS clause CASCADE;
        DROP TABLE IF EXISTS framework_version CASCADE;
        DROP TABLE IF EXISTS framework CASCADE;
        """
    )
