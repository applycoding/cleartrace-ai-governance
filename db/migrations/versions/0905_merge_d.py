"""Merge Package D (risk monitoring schema) into the main migration line."""

from __future__ import annotations

revision = "0905_merge_d"
down_revision = ("0904_merge_c", "0401_risk")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
