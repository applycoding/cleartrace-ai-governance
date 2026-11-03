from __future__ import annotations

from uuid import UUID

from cleartrace_db.session import tenant_transaction
from psycopg.types.json import Jsonb
from uuid6 import uuid7

from cleartrace_connectors.manifest import ConnectorManifest


def persist_manifest_destinations(dsn: str, tenant_id: UUID, manifest: ConnectorManifest) -> None:
    manifest_payload = {
        "name": manifest.name,
        "version": manifest.version,
        "direction": manifest.direction,
        "scopes": list(manifest.scopes),
        "field_mapping": manifest.field_mapping,
        "source_tiers": manifest.source_tiers,
        "schedule": manifest.schedule,
        "destinations": [dict(d) for d in manifest.destinations],
    }
    with tenant_transaction(dsn, tenant_id) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO connector_instance (id, tenant_id, name, manifest, enabled)
            VALUES (%s, %s, %s, %s, true)
            ON CONFLICT (tenant_id, name) DO UPDATE SET manifest = EXCLUDED.manifest
            RETURNING id
            """,
            (uuid7(), tenant_id, manifest.name, Jsonb(manifest_payload)),
        )
        row = cur.fetchone()
        if row is None:
            msg = f"connector_instance upsert returned no id for {manifest.name}"
            raise RuntimeError(msg)
        connector_id = row[0]
        cur.execute(
            "DELETE FROM egress_destination_profile WHERE tenant_id = %s AND connector_instance_id = %s",
            (tenant_id, connector_id),
        )
        for dest in manifest.destinations:
            host = str(dest.get("host", ""))
            port = int(dest.get("port", 443))
            cur.execute(
                """
                INSERT INTO egress_destination_profile (
                  id, tenant_id, connector_instance_id, host, port, cidr, mtls_required
                ) VALUES (%s, %s, %s, %s, %s, NULL, false)
                """,
                (uuid7(), tenant_id, connector_id, host, port),
            )
