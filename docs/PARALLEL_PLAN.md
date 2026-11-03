# Parallel build plan (blueprint steps 4–19)

Six work packages can proceed in parallel after this foundation PR merges. Each package owns distinct folders and consumes the shared contracts under `api/`, `packages/cleartrace-contracts/`, and `db/` (read-only unless listed).

## Shared contracts (already in main after this PR)

| Contract | Path |
|---|---|
| OpenAPI 3.1 outline | `api/openapi.yaml` |
| AsyncAPI (NATS) | `api/asyncapi.yaml` |
| Evaluation JSON Schema | `api/json-schemas/evaluation-contract.json` |
| Connector manifest | `api/json-schemas/connector-manifest.json` |
| Pydantic models + protocols | `packages/cleartrace-contracts/` |
| Cedar authz policy | `policies/cedar/authz.cedar` |
| Database schema + RLS | `db/migrations/` |

## Merge order

1. **Foundation (this PR)** — steps 1–3, contracts, Compose, CI skeleton.
2. **Package A or B** — either can follow immediately (no dependency on each other).
3. **Package C** — needs register APIs from B partially; can start on connectors with stub register.
4. **Package D** — needs assessment outputs from A (engine).
5. **Package E** — needs stable OpenAPI paths from foundation + findings from A/B.
6. **Package F** — data policy/deletion depends on `db/` tables from foundation; Helm last.

---

### Package A — Engine, AIA, framework model and packs (steps 6–9)

**Owns:** `services/engine/`, `services/aia/`, `policies/rego/`, `policies/packs/`, framework-related API routers (future).

**Consumes:** evaluation contract schema, `AssessmentEngine` / `AIAEngine` protocols, Postgres framework tables (added in this package via new migrations).

**Delivers:** OPA bundles, CEL evaluator, five-state reducer, AIA parity harness, starter packs (DADM, AIA, PSD, DSD, AI Strategy, Guiding Principles).

---

### Package B — Evidence, reviewer workflow, audit ledger (steps 10–11)

**Owns:** `services/evidence/`, `services/audit/`, reviewer routes, audit routes.

**Consumes:** OpenAPI `/evidence`, `/findings/{id}/actions`, `/audit/*`; `EvidenceStore`, `AuditLedger` protocols; `db` audit tables.

**Delivers:** Hash chain ledger, checkpointer, reviewer separation-of-duties, evidence RBAC.

---

### Package C — Register, connectors, egress, policy watcher (steps 5, 12, 14)

**Owns:** `services/connectors/`, `services/egress-proxy/`, `services/policy-watch/`, register API module.

**Consumes:** connector manifest schema, AsyncAPI subjects, outbox table, NATS in Compose.

**Delivers:** GC AI Register CSV import, MLflow/OTel/OpenLineage connectors, SSRF-safe egress proxy, policy diff pipeline.

---

### Package D — Risk engine and metrics (step 13)

**Owns:** `services/risk/`.

**Consumes:** `/metrics`, `/observations`, `RiskEngine` protocol; observation tables (new migrations).

**Delivers:** Metric registry, baselines, Evidently/Fairlearn evaluators, binding vs advisory breaches.

---

### Package E — Notifier, reports, web UI EN/FR (steps 15–16)

**Owns:** `services/notifier/`, `services/reports/`, `web/`.

**Consumes:** OpenAPI `/reports`, `/notifications`, `/webhooks`; i18n keys in `web/locales/en` and `web/locales/fr`.

**Delivers:** Alerts, EN/FR PDF/HTML reports, Next.js workflows, Playwright journeys.

---

### Package F — Data policy, interop, Helm, offline bundle, fixtures (steps 4, 17–19)

**Owns:** `deploy/helm/`, `deploy/offline-bundle/`, interop exporters, `tests/fixtures/`, `tests/fixtures/LICENSES.md`.

**Consumes:** OpenAPI `/data-policy`, `/export/oscal`, `/capabilities`; deletion tables in `db/`.

**Delivers:** Retention/legal hold/deletion certificates, OSCAL five-state exports, CycloneDX 1.6, signed offline bundle, frozen public fixtures.

---

## Coordination rules

- One migration chain in `db/migrations/` — coordinate version numbers in `#cleartrace-db` chat before merging.
- OpenAPI changes require a short note in the PR body and an entry in `docs/adr/` if breaking.
- Do not add copyleft dependencies; CI licence gate must stay green.
