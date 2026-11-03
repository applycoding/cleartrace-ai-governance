"""Merge Package C (register, connectors, policy watcher) into the main migration line.

Package A (0101) and Package C (0301) both planned system_group,
system_group_member and reassessment_flag. The Package A tables are kept;
this revision adds the Package C fields to reassessment_flag so a flag can
name the control and the policy diff that raised it.

It also withdraws UPDATE and DELETE on append-only tables from the
application role. An earlier 0101 granted UPDATE on every table, which
undid the narrower grants made by 0001 and 0201 on databases already
migrated with it.
"""

from __future__ import annotations

from alembic import op

revision = "0904_merge_c"
down_revision = ("0903_merge_f", "0301_package_c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE reassessment_flag
          ADD COLUMN control_id TEXT,
          ADD COLUMN policy_diff_id UUID REFERENCES policy_diff(id);

        REVOKE UPDATE, DELETE ON role_assignment, ai_system_version,
          decision_record, audit_pii, merkle_checkpoint
        FROM cleartrace_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE reassessment_flag
          DROP COLUMN IF EXISTS policy_diff_id,
          DROP COLUMN IF EXISTS control_id;
        """
    )
