# ClearTrace

ClearTrace is an AI governance platform for Canadian federal use: it keeps a register of AI systems, assesses them against policy packs (DADM, AIA, and others), records five-state findings with evidence, supports human review with a tamper-evident audit trail, and connects data, model, and output risk signals to governance workflows. The product is bilingual (English and French) and designed for multi-tenant deployment on-premises or in Canadian cloud.

Design authority lives in [docs/blueprint/BLUEPRINT.md](docs/blueprint/BLUEPRINT.md). Requirement-to-test mapping is in [docs/blueprint/traceability.md](docs/blueprint/traceability.md).

## TRL 5 status (honest)

The integrated API, database, NATS, and service packages are wired on `main`, and automated suites cover many essential tests (policy diff, connectors, five-state reducer, reviewer workflow, risk breaches, audit verification, SBOM licence gate, and others). Several bid tests are **not** fully met yet: second-environment install and cosign signing (T-19), same-VM backup restore timing (T-05), full security suite mapping (T-26), large-scale multi-tenant and performance tests (T-21, T-27, T-29), deferred contract-period items (T-24, T-25, T-30), and human-only gates for T-08 and T-20 (reviewer names and language review sheets stay blank). See [docs/trl5/TRL5_TEST_REPORT.md](docs/trl5/TRL5_TEST_REPORT.md) after CI generates it from JUnit results.

## Development stack

1. Install dependencies: `uv sync --all-packages --group dev`
2. Start infrastructure: `bash scripts/ci_compose_stack.sh` (Postgres 16, PgBouncer, NATS, and related services)
3. Run database migrations: `CLEARTRACE_MIGRATOR_DSN=postgresql://cleartrace_super:cleartrace_super@127.0.0.1:5432/cleartrace uv run alembic -c db/alembic.ini upgrade head`
4. Run the API locally: `CLEARTRACE_DEV_SKIP_AUTH=1 CLEARTRACE_DEV_AUTH_TOKEN=dev-token uv run cleartrace-api`

## Tests

- **Unit / fast:** `uv run pytest -q tests services --ignore=tests/integration -m "not integration"`
- **Integration / TRL 5 (needs Compose stack):** set `CLEARTRACE_TEST_DSN`, `CLEARTRACE_MIGRATOR_DSN`, `CLEARTRACE_NOTIFIER_DSN`, and `CLEARTRACE_NATS_URL`, then `uv run pytest -q tests/integration tests/trl5 services`
- **Lint:** `uv run ruff check .`, `uv run mypy packages/cleartrace-contracts/src services/core-api/src services/engine/src services/aia/src services/evidence/src services/audit/src services/notifier/src services/reports/src services/register/src services/connectors/src services/egress-proxy/src services/policy-watch/src services/risk/src db/src`, `uv run bandit -r packages services db -q`
- **TRL 5 report:** `uv run python tools/trl5_report.py --junit-unit artifacts/junit-unit.xml --junit-integration artifacts/junit-integration.xml`

Author: Arpan Bom, Tri-Vision AI & Robotics Inc. Licence: Apache-2.0.
