"""Join the Package B and Package E migration branches.

Revision ID: 0901_merge_b_e
Revises: 0201_evidence_review_audit, 0502_notifier_rls
"""

from __future__ import annotations

revision = "0901_merge_b_e"
down_revision = ("0201_evidence_review_audit", "0502_notifier_rls")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No schema change; this revision only joins two branches."""


def downgrade() -> None:
    """No schema change; this revision only joins two branches."""
