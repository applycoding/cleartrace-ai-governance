from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from cleartrace_register.csv_import import RegisterStore
from cleartrace_register.precedence import FieldUpdate

from cleartrace_connectors.builtin import (
    load_aia_json_fixture,
    load_generic_csv_fixture,
    load_mlflow_fixture,
    load_openlineage_fixture,
    load_otel_fixture,
    load_ticket_simulator_fixture,
)
from cleartrace_connectors.manifest import ConnectorManifest
from cleartrace_connectors.mapping import apply_field_mapping, fill_all_categories
from cleartrace_connectors.outbox import InMemoryOutbox, NatsJetStreamConsumer


class ConnectorRuntime:
    """Run manifest-configured connectors without custom code."""

    def __init__(self, store: RegisterStore | None = None) -> None:
        self.store = store or RegisterStore()
        self.engine = self.store.engine
        self.outbox = InMemoryOutbox()
        self.consumer = NatsJetStreamConsumer()

    def load_manifest(self, path: Path) -> ConnectorManifest:
        return ConnectorManifest.load_path(path)

    def run_manifest_for_system(
        self,
        manifest: ConnectorManifest,
        *,
        system_id: UUID,
        fixture_name: str,
        tenant_id: UUID | None = None,
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
        if tenant_id is not None:
            self.outbox.enqueue(
                tenant_id,
                subject=f"cleartrace.connector.{manifest.name}.ingest",
                payload={"system_id": str(system_id), "count": len(updates)},
            )
        return updates

    def run_t02_pipeline(
        self,
        manifests_dir: Path,
        systems: list[tuple[UUID, str, dict[int, tuple[str, str]]]],
        tenant_id: UUID,
    ) -> int:
        filled = 0
        for system_id, _key, category_values in systems:
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
                self.run_manifest_for_system(
                    manifest, system_id=system_id, fixture_name=fixture, tenant_id=tenant_id
                )
            filled += self.store.filled_category_count(system_id)
        return filled

    async def flush_outbox_to_nats(self) -> int:
        batch = self.outbox.publish_batch()
        return await self.consumer.consume(batch)

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
