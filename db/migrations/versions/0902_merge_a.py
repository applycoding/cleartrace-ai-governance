"""Merge Package A into the main migration line and link findings to assessment runs.

Package A (0101) and Package B (0201) both planned finding tables. The
Package B tables are kept; this revision adds the Package A assessment
fields to them so each finding can record the assessment run, the control
version and the engine bundle digest it used, and each finding version can
hold its EN/FR explanation.
"""

from __future__ import annotations

from alembic import op

revision = "0902_merge_a"
down_revision = ("0901_merge_b_e", "0101_package_a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE finding
          ADD COLUMN assessment_run_id UUID REFERENCES assessment_run(id),
          ADD COLUMN control_version_id UUID REFERENCES control_version(id),
          ADD COLUMN engine_bundle_digest TEXT;

        ALTER TABLE finding_version
          ADD COLUMN explanation_en TEXT,
          ADD COLUMN explanation_fr TEXT;

        CREATE INDEX idx_finding_assessment_run ON finding (assessment_run_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_finding_assessment_run;

        ALTER TABLE finding_version
          DROP COLUMN IF EXISTS explanation_fr,
          DROP COLUMN IF EXISTS explanation_en;

        ALTER TABLE finding
          DROP COLUMN IF EXISTS engine_bundle_digest,
          DROP COLUMN IF EXISTS control_version_id,
          DROP COLUMN IF EXISTS assessment_run_id;
        """
    )
