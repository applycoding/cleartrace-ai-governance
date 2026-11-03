"""Merge Package F (data policy) into the main migration line."""

from __future__ import annotations

revision = "0903_merge_f"
down_revision = ("0902_merge_a", "0601_data_policy")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No schema change; this revision joins two migration branches."""


def downgrade() -> None:
    """No schema change; this revision joins two migration branches."""
