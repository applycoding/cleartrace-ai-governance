"""Package D: metric registry, baselines, observations, risks, data quality issues."""

from __future__ import annotations

from alembic import op

revision = "0401_risk"
down_revision = "0002_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE metric_definition (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          code TEXT NOT NULL,
          area TEXT NOT NULL,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL,
          library TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, code)
        );

        CREATE TABLE metric_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          metric_definition_id UUID NOT NULL REFERENCES metric_definition(id),
          version_number INT NOT NULL,
          unit TEXT NOT NULL,
          window_kind TEXT NOT NULL,
          aggregation TEXT NOT NULL,
          config JSONB NOT NULL DEFAULT '{}'::jsonb,
          valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
          valid_to TIMESTAMPTZ,
          UNIQUE (metric_definition_id, version_number)
        );

        CREATE TABLE metric_baseline (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          metric_version_id UUID NOT NULL REFERENCES metric_version(id),
          dataset_version TEXT NOT NULL,
          baseline_value DOUBLE PRECISION NOT NULL,
          stats JSONB NOT NULL DEFAULT '{}'::jsonb,
          approver_principal_id UUID REFERENCES principal(id),
          approved_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE metric_threshold (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          metric_version_id UUID NOT NULL REFERENCES metric_version(id),
          warn_value DOUBLE PRECISION,
          breach_value DOUBLE PRECISION NOT NULL,
          higher_is_worse BOOLEAN NOT NULL DEFAULT true,
          binding BOOLEAN NOT NULL DEFAULT false,
          linked_control_id UUID,
          name_en TEXT NOT NULL,
          name_fr TEXT NOT NULL
        );

        CREATE TABLE metric_observation (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          metric_version_id UUID NOT NULL REFERENCES metric_version(id),
          window_start TIMESTAMPTZ NOT NULL,
          window_end TIMESTAMPTZ NOT NULL,
          value DOUBLE PRECISION NOT NULL,
          status TEXT NOT NULL,
          details JSONB NOT NULL DEFAULT '{}'::jsonb,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE data_quality_issue (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          observation_id UUID NOT NULL REFERENCES metric_observation(id),
          dataset_version TEXT NOT NULL,
          defect_type TEXT NOT NULL,
          linked_control_id UUID,
          trace JSONB NOT NULL,
          status TEXT NOT NULL DEFAULT 'open',
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE risk_item (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          category TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'draft',
          owner_principal_id UUID REFERENCES principal(id),
          next_review_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE risk_item_version (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          risk_item_id UUID NOT NULL REFERENCES risk_item(id),
          likelihood SMALLINT NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
          impact SMALLINT NOT NULL CHECK (impact BETWEEN 1 AND 5),
          inherent_score SMALLINT NOT NULL,
          residual_score SMALLINT NOT NULL,
          summary_en TEXT NOT NULL,
          summary_fr TEXT NOT NULL,
          valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
          valid_to TIMESTAMPTZ,
          recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE monitoring_alert (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          observation_id UUID REFERENCES metric_observation(id),
          severity TEXT NOT NULL,
          binding BOOLEAN NOT NULL,
          message_en TEXT NOT NULL,
          message_fr TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE control_outcome_override (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES tenant(id),
          linked_control_id UUID NOT NULL,
          ai_system_id UUID NOT NULL REFERENCES ai_system(id),
          observation_id UUID NOT NULL REFERENCES metric_observation(id),
          previous_outcome TEXT NOT NULL,
          new_outcome TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        ALTER TABLE metric_definition ENABLE ROW LEVEL SECURITY;
        ALTER TABLE metric_definition FORCE ROW LEVEL SECURITY;
        ALTER TABLE metric_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE metric_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE metric_baseline ENABLE ROW LEVEL SECURITY;
        ALTER TABLE metric_baseline FORCE ROW LEVEL SECURITY;
        ALTER TABLE metric_threshold ENABLE ROW LEVEL SECURITY;
        ALTER TABLE metric_threshold FORCE ROW LEVEL SECURITY;
        ALTER TABLE metric_observation ENABLE ROW LEVEL SECURITY;
        ALTER TABLE metric_observation FORCE ROW LEVEL SECURITY;
        ALTER TABLE data_quality_issue ENABLE ROW LEVEL SECURITY;
        ALTER TABLE data_quality_issue FORCE ROW LEVEL SECURITY;
        ALTER TABLE risk_item ENABLE ROW LEVEL SECURITY;
        ALTER TABLE risk_item FORCE ROW LEVEL SECURITY;
        ALTER TABLE risk_item_version ENABLE ROW LEVEL SECURITY;
        ALTER TABLE risk_item_version FORCE ROW LEVEL SECURITY;
        ALTER TABLE monitoring_alert ENABLE ROW LEVEL SECURITY;
        ALTER TABLE monitoring_alert FORCE ROW LEVEL SECURITY;
        ALTER TABLE control_outcome_override ENABLE ROW LEVEL SECURITY;
        ALTER TABLE control_outcome_override FORCE ROW LEVEL SECURITY;
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON metric_definition
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON metric_version
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON metric_baseline
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON metric_threshold
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON metric_observation
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON data_quality_issue
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON risk_item
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON risk_item_version
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON monitoring_alert
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON control_outcome_override
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS control_outcome_override;
        DROP TABLE IF EXISTS monitoring_alert;
        DROP TABLE IF EXISTS risk_item_version;
        DROP TABLE IF EXISTS risk_item;
        DROP TABLE IF EXISTS data_quality_issue;
        DROP TABLE IF EXISTS metric_observation;
        DROP TABLE IF EXISTS metric_threshold;
        DROP TABLE IF EXISTS metric_baseline;
        DROP TABLE IF EXISTS metric_version;
        DROP TABLE IF EXISTS metric_definition;
        """
    )
