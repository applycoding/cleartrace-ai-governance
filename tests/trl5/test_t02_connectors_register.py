from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID

import pytest
from cleartrace_connectors.manifest import ConnectorManifest
from cleartrace_connectors.runtime import ConnectorRuntime
from cleartrace_register.categories import category_by_number
from uuid6 import uuid7


def count_processed_events(dsn: str) -> int:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SET ROLE cleartrace_app")
        cur.execute("SELECT count(*) FROM processed_event_ids")
        row = cur.fetchone()
        return int(row[0]) if row else 0


MANIFESTS = Path(__file__).resolve().parents[2] / "services" / "connectors" / "manifests"

T02_SYSTEMS: list[tuple[str, dict[int, tuple[str, str]]]] = [
    (
        "sys-01",
        {
            1: ("Metadata EN 1", "Métadonnées FR 1"),
            2: ("Owner EN 1", "Propriétaire FR 1"),
            3: ("Intent EN 1", "Intention FR 1"),
            4: ("Pilot", "Pilote"),
            5: ("Funded", "Financé"),
            6: ("Users EN 1", "Utilisateurs FR 1"),
            7: ("Objective EN 1", "Objectif FR 1"),
            8: ("Risk EN 1", "Risque FR 1"),
            9: ("Level II", "Niveau II"),
            10: ("Partially met", "Partiellement satisfait"),
            11: ("12 artefacts", "12 artefacts"),
            12: ("metric ok", "métrique ok"),
            13: ("Approved", "Approuvé"),
            14: ("Validated", "Validé"),
            15: ("DADM assigned", "DADM assigné"),
        },
    ),
    (
        "sys-02",
        {
            1: ("Metadata EN 2", "Métadonnées FR 2"),
            2: ("Owner EN 2", "Propriétaire FR 2"),
            3: ("Intent EN 2", "Intention FR 2"),
            4: ("In production", "En production"),
            5: ("Funded", "Financé"),
            6: ("Users EN 2", "Utilisateurs FR 2"),
            7: ("Objective EN 2", "Objectif FR 2"),
            8: ("Risk EN 2", "Risque FR 2"),
            9: ("Level III", "Niveau III"),
            10: ("Not met", "Non satisfait"),
            11: ("8 artefacts", "8 artefacts"),
            12: ("metric warn", "métrique alerte"),
            13: ("Pending", "En attente"),
            14: ("Rejected", "Rejeté"),
            15: ("PSD assigned", "PSD assigné"),
        },
    ),
    (
        "sys-03",
        {
            1: ("Metadata EN 3", "Métadonnées FR 3"),
            2: ("Owner EN 3", "Propriétaire FR 3"),
            3: ("Intent EN 3", "Intention FR 3"),
            4: ("Conception", "Conception"),
            5: ("Unfunded", "Non financé"),
            6: ("Users EN 3", "Utilisateurs FR 3"),
            7: ("Objective EN 3", "Objectif FR 3"),
            8: ("Risk EN 3", "Risque FR 3"),
            9: ("Level I", "Niveau I"),
            10: ("Met", "Satisfait"),
            11: ("4 artefacts", "4 artefacts"),
            12: ("metric stable", "métrique stable"),
            13: ("Approved", "Approuvé"),
            14: ("Modified", "Modifié"),
            15: ("AIA assigned", "EIA assigné"),
        },
    ),
    (
        "sys-04",
        {
            1: ("Metadata EN 4", "Métadonnées FR 4"),
            2: ("Owner EN 4", "Propriétaire FR 4"),
            3: ("Intent EN 4", "Intention FR 4"),
            4: ("Retired", "Retiré"),
            5: ("Closed", "Clôturé"),
            6: ("Users EN 4", "Utilisateurs FR 4"),
            7: ("Objective EN 4", "Objectif FR 4"),
            8: ("Risk EN 4", "Risque FR 4"),
            9: ("Level IV", "Niveau IV"),
            10: ("Unable", "Indéterminé"),
            11: ("20 artefacts", "20 artefacts"),
            12: ("metric breach", "métrique dépassée"),
            13: ("Expired", "Expiré"),
            14: ("Annotated", "Annoté"),
            15: ("Crosswalk assigned", "Cartographie assignée"),
        },
    ),
    (
        "sys-05",
        {
            1: ("Metadata EN 5", "Métadonnées FR 5"),
            2: ("Owner EN 5", "Propriétaire FR 5"),
            3: ("Intent EN 5", "Intention FR 5"),
            4: ("In development", "En développement"),
            5: ("Funded", "Financé"),
            6: ("Users EN 5", "Utilisateurs FR 5"),
            7: ("Objective EN 5", "Objectif FR 5"),
            8: ("Risk EN 5", "Risque FR 5"),
            9: ("Level II", "Niveau II"),
            10: ("Partially met", "Partiellement satisfait"),
            11: ("6 artefacts", "6 artefacts"),
            12: ("metric ok", "métrique ok"),
            13: ("Approved", "Approuvé"),
            14: ("Validated", "Validé"),
            15: ("Strategy assigned", "Stratégie assignée"),
        },
    ),
    (
        "sys-06",
        {
            1: ("Metadata EN 6", "Métadonnées FR 6"),
            2: ("Owner EN 6", "Propriétaire FR 6"),
            3: ("Intent EN 6", "Intention FR 6"),
            4: ("Pilot", "Pilote"),
            5: ("Funded", "Financé"),
            6: ("Users EN 6", "Utilisateurs FR 6"),
            7: ("Objective EN 6", "Objectif FR 6"),
            8: ("Risk EN 6", "Risque FR 6"),
            9: ("Level III", "Niveau III"),
            10: ("Met", "Satisfait"),
            11: ("10 artefacts", "10 artefacts"),
            12: ("metric ok", "métrique ok"),
            13: ("Approved", "Approuvé"),
            14: ("Validated", "Validé"),
            15: ("Principles assigned", "Principes assignés"),
        },
    ),
]


@pytest.mark.asyncio
async def test_t02_connectors_fill_fifteen_categories_for_six_systems(
    trl_dsn: str, trl_tenant_id: UUID, nats_url: str
) -> None:
    runtime = ConnectorRuntime(trl_dsn, trl_tenant_id)
    systems: list[tuple[UUID, str, dict[int, tuple[str, str]]]] = []
    for key, categories in T02_SYSTEMS:
        system_id = uuid7()
        unique_key = f"{key}-{system_id}"
        systems.append((system_id, unique_key, categories))

    setup_start = time.perf_counter()
    for connector_file in MANIFESTS.glob("*.yaml"):
        ConnectorManifest.load_path(connector_file)
    setup_seconds = time.perf_counter() - setup_start
    assert setup_seconds <= 15 * 60, f"Manifest setup took {setup_seconds:.2f}s"

    filled_total = runtime.run_t02_pipeline(MANIFESTS, systems)
    assert filled_total == 90

    correct = 0
    for system_id, _key, expected in systems:
        for cat_num, (en, fr) in expected.items():
            cat = category_by_number(cat_num)
            val = runtime.store.get_value(system_id, cat_num, cat.primary_slot)
            assert val is not None
            if val.value_en == en and val.value_fr == fr:
                correct += 1
    assert correct == 90

    processed_before = count_processed_events(trl_dsn)
    published, consumed = await runtime.flush_outbox_to_nats(nats_url)
    assert published == len(systems) * 6
    assert consumed == published
    assert count_processed_events(trl_dsn) - processed_before == published

    published_again, consumed_again = await runtime.flush_outbox_to_nats(nats_url)
    assert published_again == 0
    assert consumed_again == 0


def test_t02_new_simulator_manifest_without_code() -> None:
    manifest_path = MANIFESTS / "ticket_simulator.yaml"
    manifest = ConnectorManifest.load_path(manifest_path)
    assert manifest.name == "ticket-simulator"
    assert manifest.field_mapping
