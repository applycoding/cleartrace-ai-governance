"""Seed cells, tenants, roles for local and test environments."""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0002_seed"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

TENANTS = [
    ("11111111-1111-7111-8111-111111111101", "tenant-alpha", "Alpha Department", "Ministère Alpha"),
    ("11111111-1111-7111-8111-111111111102", "tenant-beta", "Beta Department", "Ministère Beta"),
    ("11111111-1111-7111-8111-111111111103", "tenant-gamma", "Gamma Department", "Ministère Gamma"),
]

CELL = (
    "22222222-2222-7222-8222-222222222222",
    "ca-onprem-ssc",
    "SSC on-premises cell",
    "Cellule SSC sur site",
    "CA",
)

ROLES = [
    ("platform_operator", "Platform operator", "Opérateur de plateforme"),
    ("tenant_admin", "Tenant admin", "Administrateur locataire"),
    ("policy_steward", "Policy steward", "Gestionnaire des politiques"),
    ("system_owner", "System owner", "Propriétaire du système"),
    ("assessor", "Assessor", "Évaluateur"),
    ("oversight_reviewer", "Oversight reviewer", "Réviseur de surveillance"),
    ("approver", "Approver", "Approbateur"),
    ("auditor", "Auditor", "Auditeur"),
    ("read_only_viewer", "Read-only viewer", "Lecteur seul"),
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        text(
            """
            INSERT INTO cell (id, slug, name_en, name_fr, jurisdiction)
            VALUES (:id, :slug, :name_en, :name_fr, :jurisdiction)
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": CELL[0],
            "slug": CELL[1],
            "name_en": CELL[2],
            "name_fr": CELL[3],
            "jurisdiction": CELL[4],
        },
    )
    for tid, slug, name_en, name_fr in TENANTS:
        bind.execute(
            text(
                """
                INSERT INTO tenant (id, slug, name_en, name_fr)
                VALUES (:id, :slug, :name_en, :name_fr)
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": tid, "slug": slug, "name_en": name_en, "name_fr": name_fr},
        )
        bind.execute(
            text(
                """
                INSERT INTO tenant_cell_binding (tenant_id, cell_id)
                VALUES (:tenant_id, :cell_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"tenant_id": tid, "cell_id": CELL[0]},
        )
    for code, name_en, name_fr in ROLES:
        bind.execute(
            text(
                """
                INSERT INTO app_role (id, code, name_en, name_fr)
                VALUES (gen_random_uuid(), :code, :name_en, :name_fr)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "name_en": name_en, "name_fr": name_fr},
        )


def downgrade() -> None:
    op.execute("DELETE FROM tenant_cell_binding")
    op.execute("DELETE FROM tenant")
    op.execute("DELETE FROM cell")
    op.execute("DELETE FROM app_role")
