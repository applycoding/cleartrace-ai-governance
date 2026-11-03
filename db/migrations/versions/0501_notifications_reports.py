"""Package E: notifications, webhooks, tickets, report jobs."""

from __future__ import annotations

from alembic import op

revision = "0501_notifications"
down_revision = "0002_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_subscription (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            url TEXT NOT NULL,
            secret TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT 'generic',
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS notification (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            alert_type TEXT NOT NULL,
            system_id UUID,
            control_id TEXT,
            reason TEXT NOT NULL,
            title_en TEXT NOT NULL,
            title_fr TEXT NOT NULL,
            body_en TEXT NOT NULL,
            body_fr TEXT NOT NULL,
            dedup_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delivered_at TIMESTAMPTZ
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_dedup_open
            ON notification (tenant_id, dedup_key)
            WHERE status IN ('pending', 'delivered');

        CREATE TABLE IF NOT EXISTS ticket_link (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            notification_id UUID NOT NULL REFERENCES notification (id),
            external_system TEXT NOT NULL,
            external_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            dedup_key TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_ticket_dedup_open
            ON ticket_link (tenant_id, dedup_key)
            WHERE status = 'open';

        CREATE TABLE IF NOT EXISTS webhook_delivery (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            notification_id UUID NOT NULL REFERENCES notification (id),
            subscription_id UUID NOT NULL REFERENCES webhook_subscription (id),
            attempt INTEGER NOT NULL,
            status TEXT NOT NULL,
            response_code INTEGER,
            error_message TEXT,
            next_retry_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS dead_letter_queue (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            notification_id UUID NOT NULL REFERENCES notification (id),
            subscription_id UUID NOT NULL REFERENCES webhook_subscription (id),
            reason TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS report_job (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            report_type TEXT NOT NULL,
            language TEXT NOT NULL,
            format TEXT NOT NULL,
            scope JSONB NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'queued',
            artefact_uri TEXT,
            as_of TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS processed_event_ids (
            tenant_id UUID NOT NULL REFERENCES tenant (id),
            event_id TEXT NOT NULL,
            processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (tenant_id, event_id)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS processed_event_ids;
        DROP TABLE IF EXISTS report_job;
        DROP TABLE IF EXISTS dead_letter_queue;
        DROP TABLE IF EXISTS webhook_delivery;
        DROP TABLE IF EXISTS ticket_link;
        DROP TABLE IF EXISTS notification;
        DROP TABLE IF EXISTS webhook_subscription;
        """
    )
