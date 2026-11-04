# ClearTrace

ClearTrace is an AI governance platform for Canadian federal use: it keeps a register of AI systems, assesses them against policy packs (DADM, AIA, and others), records five-state findings with evidence, supports human review with a tamper-evident audit trail, and connects data, model, and output risk signals to governance workflows. The product is bilingual (English and French) and designed for multi-tenant deployment on-premises or in Canadian cloud.

Design authority lives in [docs/blueprint/BLUEPRINT.md](docs/blueprint/BLUEPRINT.md). Requirement-to-test mapping is in [docs/blueprint/traceability.md](docs/blueprint/traceability.md).

## TRL 5 status (honest)

The integrated API, database, NATS, and service packages are wired on `main`, and automated suites cover many essential tests (policy diff, connectors, five-state reducer, reviewer workflow, risk breaches, audit verification, SBOM licence gate, and others). Several bid tests are **not** fully met yet: second-environment install and cosign signing (T-19), same-VM backup restore timing (T-05), full security suite mapping (T-26), large-scale multi-tenant and performance tests (T-21, T-27, T-29), and deferred contract-period items (T-24, T-25, T-30). Human gates **T-08** and **T-20** stay **partial** until the review sheets in `docs/trl5/` are fully scored (T-08: 133/140 pairs marked correct by both reviewers, the section 18 bar; T-20: at least 95% of rows accepted, a ClearTrace bar). T-08 also stays partial after review because its 40 seeded non-conformities cover only 3 shipped controls. While the sheets are blank the T-08 review test is an expected failure (xfail) and the T-20 sheet test checks only that the sheet is complete and blank. See [docs/trl5/TRL5_TEST_REPORT.md](docs/trl5/TRL5_TEST_REPORT.md) (regenerate locally; do not overwrite the committed CI snapshot without `--output`).

## Development stack

1. Install dependencies: `uv sync --all-packages --group dev`
2. Install OPA for engine tests and generators: `bash scripts/install_opa.sh` (sets `OPA_BIN` if needed)
3. Start infrastructure: `bash scripts/ci_compose_stack.sh` (Postgres 16, PgBouncer, NATS, and related services)
4. Run database migrations:

   `CLEARTRACE_MIGRATOR_DSN=postgresql://cleartrace_super:cleartrace_super@127.0.0.1:5432/cleartrace uv run alembic -c db/alembic.ini upgrade head`

5. Run the API locally:

   `CLEARTRACE_DEV_SKIP_AUTH=1 CLEARTRACE_DEV_AUTH_TOKEN=dev-token uv run cleartrace-api`

### Environment DSNs (local Compose)

Use these when running integration and TRL 5 tests against the default Compose stack:

| Variable | Typical value |
| --- | --- |
| `CLEARTRACE_MIGRATOR_DSN` | `postgresql://cleartrace_super:cleartrace_super@127.0.0.1:5432/cleartrace` |
| `CLEARTRACE_TEST_DSN` | `postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace` |
| `CLEARTRACE_NOTIFIER_DSN` | same as `CLEARTRACE_TEST_DSN` |
| `CLEARTRACE_NATS_URL` | `nats://127.0.0.1:4222` |

T-05 backup/restore uses a second Postgres cluster. CI sets `CLEARTRACE_T05_RESTORE_ADMIN_DSN=postgresql://cleartrace_super:cleartrace_super@127.0.0.1:5435/postgres` and `PG_BIN=/usr/lib/postgresql/16/bin`. Locally, install Postgres 16 client tools (`postgresql-client-16` on Debian/Ubuntu) so `pg_dump`/`pg_restore` match the server, export `PG_BIN` if the binaries are not on `PATH`, and either point `CLEARTRACE_T05_RESTORE_ADMIN_DSN` at a restore instance or let the test start one on `CLEARTRACE_T05_RESTORE_PORT` (default `5435`).

## Tests

- **Unit / fast:** `uv run pytest -q tests services --ignore=tests/integration -m "not integration"`
- **Integration / TRL 5 (needs Compose stack):** export the DSNs above, then  
  `uv run pytest -q tests/integration tests/trl5 services`
- **JUnit XML (for the TRL 5 report):**

  ```bash
  mkdir -p artifacts
  uv run pytest -q tests services --ignore=tests/integration -m "not integration" --junitxml=artifacts/junit-unit.xml
  uv run pytest -q tests/integration tests/trl5 services --junitxml=artifacts/junit-integration.xml
  ```

- **T-26 security suite (after Compose + API env):**

  ```bash
  mkdir -p artifacts/t26
  export CLEARTRACE_DATABASE_URL=postgresql+psycopg://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace
  export CLEARTRACE_DEV_SKIP_AUTH=true CLEARTRACE_DEV_AUTH_TOKEN=t26-security-suite-token
  bash scripts/ci_security_suite.sh
  ```

- **TRL 5 report:** write to a fresh file so the committed report is unchanged:

  ```bash
  uv run python tools/trl5_report.py \
    --junit-unit artifacts/junit-unit.xml \
    --junit-integration artifacts/junit-integration.xml \
    --t26-summary artifacts/t26/t26_summary.json \
    --output artifacts/TRL5_TEST_REPORT.local.md
  ```

  The generator reads human review outcomes from `docs/trl5/t08_explanation_review.csv` and `docs/trl5/t20_language_review_sheet.csv`.

- **Lint:** `uv run ruff check .`, `uv run mypy packages/cleartrace-contracts/src services/core-api/src services/engine/src services/aia/src services/evidence/src services/audit/src services/notifier/src services/reports/src services/register/src services/connectors/src services/egress-proxy/src services/policy-watch/src services/risk/src db/src`, `uv run bandit -r packages services db -q`

- **Regenerate T-08 / T-20 review sheets (requires OPA):** `uv run python tools/generate_t08_cases.py` and `uv run python tools/generate_t20_review_sheet.py`

## Web UI with mock data

The Next.js app defaults to `NEXT_PUBLIC_API_BASE=http://127.0.0.1:4010/api/v1`.

1. `cd web && npm ci`
2. In one terminal: `npm run mock-api` (serves mock JSON from `web/scripts/mock-api-server.mjs`)
3. In another: `npm run dev` and open `http://127.0.0.1:3000` — switch EN/FR in the shell to exercise locale strings under test T-20.

Author: Arpan Bom, Tri-Vision AI & Robotics Inc. Licence: Apache-2.0.
