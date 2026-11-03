# Threat model (ClearTrace TRL 5)

This document summarises STRIDE threats per major component from `docs/blueprint/BLUEPRINT.md` sections 4–7 and 10. It is maintained with design changes (ASVS V1.1.2).

## Trust boundaries

| Boundary | Inside | Outside |
| --- | --- | --- |
| B1 | Core API, engine, evidence store, audit ledger (tenant-scoped) | Browser, IdP, external webhooks |
| B2 | Postgres + PgBouncer + object store | Operators, backup tools |
| B3 | OPA/Cedar policy evaluation | Pack authors (Git) |
| B4 | NATS/outbox consumers | External ticket simulators |

Data crosses B1 on every authenticated API call (bearer JWT). Tenant id and roles are taken only from validated tokens (or dev headers behind `CLEARTRACE_DEV_SKIP_AUTH`).

## STRIDE by component

### Web UI (EN/FR)

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Spoofing | Stolen session at IdP | OIDC; API uses bearer tokens only |
| Tampering | XSS altering review actions | CSP on API; UI uses JSON API |
| Repudiation | User denies submission | Audit ledger on state changes |
| Information disclosure | Cross-tenant data in UI | RLS + Cedar; tests T-06/T-21/T-29 |
| Denial of service | Flood UI/API | Per-tenant rate limits (T-21) |
| Elevation | Viewer approves finding | Cedar denies; T-06 matrix |

### Core API (FastAPI)

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Spoofing | Forged JWT | JWKS validation; generic 401 |
| Tampering | Idempotency replay across tenants | Tenant-scoped idempotency keys |
| Repudiation | Denied action not logged | `authz.denied` audit with failure logging |
| Information disclosure | IDOR on reports/register | Tenant checks on resources (T-26 fixes) |
| Denial of service | Large uploads | 25 MiB cap; rate limits |
| Elevation | SSRF via webhooks | Public HTTPS-only URLs; egress proxy |

### Engine + OPA (assessment)

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Tampering | Pack swap at runtime | Pack slug + digest in evaluation contract |
| Information disclosure | Leak other tenant evidence in CEL | Tenant context in DB session only |
| Elevation | Malicious Rego exfiltrates data | OPA bundle scoped; no network in eval |
| Repudiation | Outcome dispute | Stored inputs + rule replay (T-13) |

### Audit ledger + WORM

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Tampering | Edit/delete/reorder events | Hash chain + Merkle checkpoints (T-23) |
| Repudiation | Missing privileged read | `audit.read` logged on ledger access |
| Information disclosure | PII in audit payload | PII envelope + classification |

### Postgres / PgBouncer

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Spoofing | Shared DB user across tenants | RLS FORCE; `SET LOCAL` tenant id |
| Information disclosure | Pooling leak | T-29; `DISCARD ALL` on pool reset |
| Tampering | SQL injection | Parameterised queries |

### Object store (evidence bytes)

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Tampering | Swap artefact bytes | SHA-256 at ingest |
| Information disclosure | Unauthorized download | Role checks on evidence routes |
| Repudiation | Missing provenance | Submitter role recorded (T-12) |

### Notifications / webhooks

| STRIDE | Threat | Mitigation |
| --- | --- | --- |
| Spoofing | Fake alert injection | Authenticated dispatch API |
| Tampering | Webhook MITM | HTTPS only; optional TLS to providers |
| Denial of service | Retry storm | DLQ + dedupe (T-22) |

## Residual risks (accepted at TRL 5)

- TLS between all Compose services is optional via `deploy/compose/docker-compose.tls.yml` (self-signed); production expects ingress TLS and managed DB TLS.
- Image signing (cosign) pending (T-19).
- Human EN/FR copy review pending (T-20).
