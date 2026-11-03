"""T-06: 600 allowed + 600 forbidden requests across 3 tenants and 6 roles.

Section 18 pass criterion: "600/600 allowed succeed; 0/600 forbidden succeed; every
denial and privileged read audited". An allowed request counts only when it returns a
2xx status; a forbidden request counts only when it returns 403. Audit rows are
counted per tenant before and after the run, so the deltas must match exactly.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

import psycopg
import pytest
from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from fastapi.testclient import TestClient

from tests.trl5._helpers import migrator_dsn, pg_dsn
from tests.trl5.t06_matrix import (
    ACTIONS,
    EXPECTED_ALLOWED,
    PRIVILEGED_READ_AUDIT_ACTION,
    ROLES,
    TEMPLATES,
    TENANTS,
    Probe,
    build_matrix,
    cedar_allows,
)

pytestmark = [pytest.mark.integration, pytest.mark.trl5, pytest.mark.usefixtures("opa_server")]

TOKEN = "trl5-t06-matrix-token"
AUDIT_ACTIONS = ("authz.denied", *sorted(set(PRIVILEGED_READ_AUDIT_ACTION.values())))


def _sqlalchemy_url(dsn: str) -> str:
    return dsn.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    worm = tmp_path_factory.mktemp("worm")
    keys = tmp_path_factory.mktemp("keys")
    settings = Settings(
        dev_skip_auth=True,
        dev_auth_token=TOKEN,
        tenant_rate_limit_per_window=0,
        audit_worm_root=str(worm),
        audit_signer_key_path=str(keys / "signer.key"),
        database_url=_sqlalchemy_url(pg_dsn()),
    )
    return TestClient(create_app(settings))


def _headers(tenant_id: UUID, role: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-ClearTrace-Dev-Tenant": str(tenant_id),
        "X-ClearTrace-Dev-Roles": role,
    }


def _audit_counts() -> Counter[tuple[UUID, str]]:
    counts: Counter[tuple[UUID, str]] = Counter()
    with psycopg.connect(migrator_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT tenant_id, action, COUNT(*) FROM audit_event
            WHERE tenant_id = ANY(%s) AND action = ANY(%s)
            GROUP BY tenant_id, action
            """,
            (list(TENANTS), list(AUDIT_ACTIONS)),
        )
        for tenant_id, action, n in cur.fetchall():
            counts[(tenant_id, str(action))] = int(n)
    return counts


def _seed_systems(client: TestClient) -> dict[UUID, UUID]:
    """One system per tenant, created by its tenant_admin, for path templates."""
    systems: dict[UUID, UUID] = {}
    for tenant_id in TENANTS:
        resp = client.post(
            "/api/v1/systems",
            headers={
                **_headers(tenant_id, "tenant_admin"),
                "Idempotency-Key": f"t06-seed-{tenant_id}",
            },
            json={
                "system_key": f"t06-seed-{tenant_id.hex[-6:]}",
                "name_en": "T-06 seed",
                "name_fr": "Graine T-06",
            },
        )
        assert resp.status_code == 201, resp.text
        systems[tenant_id] = UUID(resp.json()["id"])
    return systems


def _send(client: TestClient, probe: Probe, system_id: UUID, seq: int) -> int:
    template = probe.template
    headers = _headers(probe.tenant_id, probe.role)
    unique = f"{probe.tenant_id.hex[-4:]}-{probe.role}-{seq}"
    if template.idempotent_post:
        headers["Idempotency-Key"] = f"t06-{unique}"
    body = template.body(unique, system_id)
    resp = client.request(template.method, template.path(system_id), headers=headers, json=body)
    return resp.status_code


def test_t06_expected_matrix_matches_cedar() -> None:
    mismatches = [
        (role, action)
        for role in ROLES
        for action in ACTIONS
        if (action in EXPECTED_ALLOWED[role]) != cedar_allows(action, role)
    ]
    assert not mismatches, f"hand-written matrix disagrees with Cedar: {mismatches}"


def test_t06_full_auth_matrix_and_audit(client: TestClient, record_property) -> None:
    allowed, denied = build_matrix(target_each=600)
    assert len(allowed) == 600 and len(denied) == 600
    assert {p.tenant_id for p in allowed + denied} == set(TENANTS)
    assert {p.role for p in allowed + denied} == set(ROLES)

    systems = _seed_systems(client)
    before = _audit_counts()

    allowed_ok = 0
    allowed_failures: Counter[str] = Counter()
    expected: Counter[tuple[UUID, str]] = Counter()
    for seq, probe in enumerate(allowed):
        status = _send(client, probe, systems[probe.tenant_id], seq)
        if 200 <= status < 300:
            allowed_ok += 1
            audit_action = PRIVILEGED_READ_AUDIT_ACTION.get(probe.template.action)
            if audit_action:
                expected[(probe.tenant_id, audit_action)] += 1
        else:
            t = probe.template
            allowed_failures[f"{probe.role} {t.method} {t.path(systems[probe.tenant_id])} -> {status}"] += 1

    forbidden_refused = 0
    forbidden_leaks: Counter[str] = Counter()
    for seq, probe in enumerate(denied):
        status = _send(client, probe, systems[probe.tenant_id], 10_000 + seq)
        if status == 403:
            forbidden_refused += 1
            expected[(probe.tenant_id, "authz.denied")] += 1
        else:
            t = probe.template
            forbidden_leaks[f"{probe.role} {t.method} {t.action} -> {status}"] += 1

    after = _audit_counts()
    delta = +Counter({k: after[k] - before[k] for k in set(after) | set(before)})
    denials_audited = sum(v for (_, a), v in delta.items() if a == "authz.denied")
    reads_audited = sum(v for (_, a), v in delta.items() if a != "authz.denied")

    record_property("t06_allowed_succeeded", allowed_ok)
    record_property("t06_forbidden_refused", forbidden_refused)
    record_property("t06_request_templates", len(TEMPLATES))
    record_property("t06_denials_audited", denials_audited)
    record_property("t06_privileged_reads_audited", reads_audited)

    assert allowed_ok == 600, f"allowed requests that did not succeed: {dict(allowed_failures)}"
    assert forbidden_refused == 600, f"forbidden requests not refused: {dict(forbidden_leaks)}"
    assert reads_audited > 0
    assert delta == expected, f"audit deltas {dict(delta)} != expected {dict(expected)}"
