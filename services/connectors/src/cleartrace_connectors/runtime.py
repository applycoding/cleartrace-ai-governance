from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_register.postgres_store import PostgresRegisterStore
from cleartrace_register.precedence import FieldUpdate

from cleartrace_connectors.builtin import (
    load_aia_json_fixture,
    load_generic_csv_fixture,
    load_mlflow_fixture,
    load_openlineage_fixture,
    load_otel_fixture,
    load_ticket_simulator_fixture,
)
from cleartrace_connectors.egress_profiles import persist_manifest_destinations
from cleartrace_connectors.manifest import ConnectorManifest
from cleartrace_connectors.mapping import apply_field_mapping, fill_all_categories
from cleartrace_connectors.nats_js import consume_outbox_messages, publish_outbox_batch
from cleartrace_connectors.postgres_outbox import PostgresOutbox


class ConnectorRuntime:
    """Run manifest-configured connectors against Postgres + JetStream outbox."""

    def __init__(self, dsn: str, tenant_id: UUID) -> None:
        self.dsn = dsn
        self.tenant_id = tenant_id
        self.store = PostgresRegisterStore(dsn, tenant_id)
        self.outbox = PostgresOutbox(dsn, tenant_id)
        self.engine = self.store.engine

    def load_manifest(self, path: Path) -> ConnectorManifest:
        manifest = ConnectorManifest.load_path(path)
        persist_manifest_destinations(self.dsn, self.tenant_id, manifest)
        return manifest

    def run_manifest_for_system(
        self,
        manifest: ConnectorManifest,
        *,
        system_id: UUID,
        fixture_name: str,
    ) -> list[FieldUpdate]:
        payload = self._load_fixture(manifest.name, fixture_name)
        tier = manifest.source_tiers.get("default", 2)
        updates = apply_field_mapping(
            payload,
            manifest.field_mapping,
            source_id=manifest.name,
            source_tier=tier,
            system_id=system_id,
        )
        for update in updates:
            self.store.ingest(update)
        self.outbox.enqueue(
            subject=f"cleartrace.connector.{manifest.name}.ingest",
            payload={"system_id": str(system_id), "count": len(updates)},
        )
        return updates

    def run_t02_pipeline(
        self,
        manifests_dir: Path,
        systems: list[tuple[UUID, str, dict[int, tuple[str, str]]]],
    ) -> int:
        filled = 0
        for system_id, system_key, category_values in systems:
            self.store.register_system(system_id, system_key)
            for update in fill_all_categories(
                system_id,
                source_id="register-merge",
                values_by_category=category_values,
            ):
                self.store.ingest(update)
            for connector_file, fixture in (
                ("mlflow.yaml", "default"),
                ("otel.yaml", "default"),
                ("openlineage.yaml", "default"),
                ("aia_json.yaml", "default"),
                ("ticket_simulator.yaml", "default"),
                ("generic_csv.yaml", "default"),
            ):
                manifest = self.load_manifest(manifests_dir / connector_file)
                self.run_manifest_for_system(manifest, system_id=system_id, fixture_name=fixture)
            filled += self.store.filled_category_count(system_id)
        return filled

    async def flush_outbox_to_nats(self, nats_url: str) -> tuple[int, int]:
        published = await publish_outbox_batch(
            dsn=self.dsn, tenant_id=self.tenant_id, nats_url=nats_url
        )
        consumed = await consume_outbox_messages(dsn=self.dsn, nats_url=nats_url)
        return published, consumed

    @staticmethod
    def _load_fixture(connector_name: str, fixture_name: str) -> dict[str, Any]:
        loaders = {
            "mlflow": load_mlflow_fixture,
            "otel-collector": load_otel_fixture,
            "openlineage": load_openlineage_fixture,
            "aia-json": load_aia_json_fixture,
            "ticket-simulator": load_ticket_simulator_fixture,
            "generic-csv": load_generic_csv_fixture,
        }
        loader = loaders.get(connector_name)
        if loader is None:
            msg = f"Unknown connector {connector_name}"
            raise KeyError(msg)
        return loader(fixture_name)
