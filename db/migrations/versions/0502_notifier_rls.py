"""RLS for notifier tables, idempotency, and dedup index fix."""

from __future__ import annotations

from alembic import op

revision = "0502_notifier_rls"
down_revision = "0501_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_notification_dedup_open;

        CREATE TABLE IF NOT EXISTS notifier_idempotency (
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            event_id TEXT NOT NULL,
            processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, event_id)
        );

        ALTER TABLE webhook_subscription ENABLE ROW LEVEL SECURITY;
        ALTER TABLE webhook_subscription FORCE ROW LEVEL SECURITY;
        ALTER TABLE notification ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notification FORCE ROW LEVEL SECURITY;
        ALTER TABLE ticket_link ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ticket_link FORCE ROW LEVEL SECURITY;
        ALTER TABLE webhook_delivery ENABLE ROW LEVEL SECURITY;
        ALTER TABLE webhook_delivery FORCE ROW LEVEL SECURITY;
        ALTER TABLE dead_letter_queue ENABLE ROW LEVEL SECURITY;
        ALTER TABLE dead_letter_queue FORCE ROW LEVEL SECURITY;
        ALTER TABLE report_job ENABLE ROW LEVEL SECURITY;
        ALTER TABLE report_job FORCE ROW LEVEL SECURITY;
        ALTER TABLE notifier_idempotency ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notifier_idempotency FORCE ROW LEVEL SECURITY;

        CREATE POLICY tenant_isolation ON webhook_subscription
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON notification
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON ticket_link
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON webhook_delivery
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON dead_letter_queue
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON report_job
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
        CREATE POLICY tenant_isolation ON notifier_idempotency
          USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

        ALTER TABLE webhook_subscription OWNER TO cleartrace_owner;
        ALTER TABLE notification OWNER TO cleartrace_owner;
        ALTER TABLE ticket_link OWNER TO cleartrace_owner;
        ALTER TABLE webhook_delivery OWNER TO cleartrace_owner;
        ALTER TABLE dead_letter_queue OWNER TO cleartrace_owner;
        ALTER TABLE report_job OWNER TO cleartrace_owner;
        ALTER TABLE notifier_idempotency OWNER TO cleartrace_owner;

        GRANT SELECT, INSERT, UPDATE ON webhook_subscription, notification, ticket_link,
          webhook_delivery, dead_letter_queue, report_job, notifier_idempotency TO cleartrace_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS notifier_idempotency;
        """
    )
