"""Least-privilege grants and append-only rules for Package D risk tables."""

from __future__ import annotations

from alembic import op

revision = "0906_risk_grants"
down_revision = "0905_merge_d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE metric_definition OWNER TO cleartrace_owner;
        ALTER TABLE metric_version OWNER TO cleartrace_owner;
        ALTER TABLE metric_baseline OWNER TO cleartrace_owner;
        ALTER TABLE metric_threshold OWNER TO cleartrace_owner;
        ALTER TABLE metric_observation OWNER TO cleartrace_owner;
        ALTER TABLE data_quality_issue OWNER TO cleartrace_owner;
        ALTER TABLE risk_item OWNER TO cleartrace_owner;
        ALTER TABLE risk_item_version OWNER TO cleartrace_owner;
        ALTER TABLE monitoring_alert OWNER TO cleartrace_owner;
        ALTER TABLE control_outcome_override OWNER TO cleartrace_owner;

        REVOKE ALL ON
          metric_definition, metric_version, metric_baseline, metric_threshold,
          metric_observation, data_quality_issue, risk_item, risk_item_version,
          monitoring_alert, control_outcome_override
        FROM cleartrace_app;

        GRANT SELECT, INSERT, UPDATE ON
          metric_definition, metric_version, metric_baseline, metric_threshold,
          risk_item, data_quality_issue, monitoring_alert
        TO cleartrace_app;

        GRANT SELECT, INSERT ON
          metric_observation, risk_item_version, control_outcome_override
        TO cleartrace_app;

        REVOKE UPDATE, DELETE ON
          metric_observation, risk_item_version, control_outcome_override
        FROM cleartrace_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE, DELETE ON
          metric_definition, metric_version, metric_baseline, metric_threshold,
          metric_observation, data_quality_issue, risk_item, risk_item_version,
          monitoring_alert, control_outcome_override
        TO cleartrace_app;
        """
    )
