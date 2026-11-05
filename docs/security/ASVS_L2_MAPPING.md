# ASVS 4.0.3 Level 2 mapping (not a certification)

Every OWASP ASVS 4.0.3 Level 2 requirement is listed once, in standard order, and marked **Pass**, **Fail** or **N/A** (blueprint section 18, T-26). The full ID list is in `docs/security/asvs_4.0.3_l2_ids.txt`; `tests/trl5/test_t26_security_gate.py` checks that the table covers exactly those IDs and that every file cited for a Pass exists.

- **Pass**: the evidence named in the row exists in this repository and was checked.
- **Fail**: the requirement is not met, or is not verified, at TRL 5.
- **N/A**: the feature the requirement governs does not exist in ClearTrace (for example passwords or sessions, which the OIDC identity provider owns).

Requirement text is not reproduced; see the standard. OWASP ASVS 4.0.3 is © OWASP Foundation, licensed CC BY-SA 4.0: https://github.com/OWASP/ASVS/tree/v4.0.3.

Paths in backticks are relative to the repository root; `routers/…`, `auth/…`, `middleware/…` and `errors/…` shorthand is under `services/core-api/src/cleartrace_core_api/`.

Totals: 107 Pass, 64 Fail, 88 N/A (259 requirements).

| Requirement | Status | Evidence or reason |
| --- | --- | --- |
| V1.1.1 | Pass | Build rules and CI gates: `BUILD_RULES.md`, `.github/workflows/ci.yml` (lint, type, SAST, licence, secrets, SBOM, Trivy, tests) |
| V1.1.2 | Fail | A STRIDE threat model now exists (`docs/security/THREAT_MODEL.md`), but nothing requires it to be revisited for every design change or sprint (no PR template, checklist or CI check) |
| V1.1.3 | Fail | Features are traced to blueprint requirements (`docs/blueprint/traceability.md`) but user stories carry no explicit security constraints |
| V1.1.4 | Fail | `docs/security/THREAT_MODEL.md` lists four trust boundaries, but significant data flows (API to engine/OPA, outbox to NATS, evidence to object store, notifier to webhooks) are not documented or justified per boundary |
| V1.1.5 | Fail | No documented security analysis of the high-level architecture and connected remote services |
| V1.1.6 | Pass | Central controls: auth and Cedar middleware `services/core-api/src/cleartrace_core_api/auth/middleware.py`, RLS via `db/src/cleartrace_db/session.py`, problem+json errors `services/core-api/src/cleartrace_core_api/errors/problem.py` |
| V1.1.7 | Fail | `BUILD_RULES.md` and `SECURITY.md` exist but there is no secure coding checklist for developers and testers |
| V1.2.1 | Fail | Helm chart sets no `securityContext` (runAsNonRoot, readOnlyRootFilesystem) in `deploy/helm/cleartrace/templates/deployment.yaml`; DB roles are separated (`cleartrace_app` vs migrator) in `db/migrations/versions/0001_initial_schema.py` |
| V1.2.2 | Fail | Database and NATS use static passwords or none; component-to-component calls (OPA, NATS) are not authenticated |
| V1.2.3 | Pass | Single mechanism: OIDC bearer JWT, RS256, issuer and audience checked in `services/core-api/src/cleartrace_core_api/auth/middleware.py`; dev token is blocked in Helm (`tests/unit/test_dev_auth_guard.py`) |
| V1.2.4 | Pass | Every non-public route passes the same `AuthContextMiddleware`; public paths are fixed (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V1.4.1 | Pass | Server-side enforcement in Cedar middleware and Postgres RLS: `policies/cedar/authz.cedar`, `tests/unit/test_cedar_role_matrix.py`, `tests/integration/test_rls_and_bitemporal.py` |
| V1.4.4 | Pass | All API requests pass `CedarAuthMiddleware` (`services/core-api/src/cleartrace_core_api/auth/middleware.py`); data access is tenant-scoped by RLS (`db/src/cleartrace_db/session.py`) |
| V1.4.5 | Fail | Cedar decisions are per route action and role (`services/core-api/src/cleartrace_core_api/auth/route_actions.py`); no per-data-item attribute checks beyond tenant |
| V1.5.1 | Fail | No documented input/output handling requirements per data type and applicable law |
| V1.5.2 | Pass | Clients exchange JSON only; no native object serialization (`api/openapi.yaml`) |
| V1.5.3 | Pass | Pydantic request models validate on the server (`services/core-api/src/cleartrace_core_api/routers/`), plus `services/core-api/src/cleartrace_core_api/middleware/json_input_guard.py` |
| V1.5.4 | Pass | Responses are JSON-encoded by the framework; SQL is parameterized at the driver (`services/core-api/src/cleartrace_core_api/routers/systems.py`) |
| V1.6.1 | Fail | No key management policy or key lifecycle standard |
| V1.6.2 | Fail | Master key comes from an environment variable or a per-process random key (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`); there is no key vault or KMS |
| V1.6.3 | Fail | No documented key rotation or re-encryption process |
| V1.6.4 | Pass | No client-side secrets protect data; the web shell only carries the user's bearer token (`web/`) |
| V1.7.1 | Pass | One API process (`cleartrace-api`) with all services in-process; `services/core-api/src/cleartrace_core_api/logging_setup.py` applies one stdlib logging format to every logger, JSON when `CLEARTRACE_JSON_LOGS` is set (`docs/config/logging.json.example`) |
| V1.7.2 | Fail | Logs are not shipped to a remote system |
| V1.8.1 | Pass | Classification ceiling and data classes per tenant: `db/migrations/versions/0601_data_policy.py`, `services/core-api/src/cleartrace_core_api/data_policy/models.py` |
| V1.8.2 | Fail | Retention is defined per artefact class (`services/core-api/src/cleartrace_core_api/data_policy/service.py`) but encryption and integrity requirements per protection level are not defined |
| V1.9.1 | Fail | Only the PgBouncer to Postgres hop can use TLS (optional overlay `deploy/compose/docker-compose.tls.yml`); API to PgBouncer, NATS and OPA stay plaintext, and the default Compose file has no TLS |
| V1.9.2 | Fail | No mutual authentication or certificate verification between components |
| V1.10.1 | Fail | Git with pull requests and CI, but nothing requires a commit or PR to reference an issue or change ticket |
| V1.11.1 | Pass | Services and their functions are listed in `docs/blueprint/BLUEPRINT.md` and `README.md` |
| V1.11.2 | Fail | Several API routes keep state in per-process dictionaries (`services/core-api/src/cleartrace_core_api/routers/systems.py`, `routers/reports.py`), not synchronized across replicas |
| V1.12.2 | Pass | Evidence files are stored as bytes and not served inline; reports download as attachments (`services/core-api/src/cleartrace_core_api/routers/reports.py`) |
| V1.14.1 | Fail | No network policies or API gateway segregation in `deploy/helm/cleartrace/templates/` |
| V1.14.2 | Fail | Images are not signed (cosign pending, see T-19 in `docs/trl5/TRL5_TEST_REPORT.md`) |
| V1.14.3 | Pass | Trivy fails the build on fixable critical/high issues and the SBOM is generated (`.github/workflows/ci.yml`) |
| V1.14.4 | Pass | CI builds, tests and scans every candidate before main moves (`.github/workflows/ci.yml`) |
| V1.14.5 | Fail | Containers run without sandboxing or network policies (`deploy/helm/cleartrace/templates/deployment.yaml`) |
| V1.14.6 | Pass | The web shell is a TypeScript app with no plugins or applets (`web/package.json`) |
| V2.1.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.4 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.5 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.6 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.7 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.8 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.9 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.10 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.11 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.1.12 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.2.1 | Fail | Login is at the IdP, but API brute-force is only limited per tenant (`services/core-api/src/cleartrace_core_api/middleware/tenant_rate_limit.py`); no per-client anti-automation on token failures |
| V2.2.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.2.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.3.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.3.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.3.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.4.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.4.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.4.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.4.4 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.4.5 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.4 | Fail | Compose and CI use shared default service accounts (`cleartrace_super`, `cleartrace_app`) in `deploy/compose/docker-compose.yml` |
| V2.5.5 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.6 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.5.7 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.6.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.6.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.6.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.4 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.5 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.7.6 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.4 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.5 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.6 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.8.7 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.9.1 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.9.2 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.9.3 | N/A | Authentication is delegated to the OIDC identity provider (Keycloak); the application has no passwords, OTP, recovery or authenticator handling of its own (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V2.10.1 | Fail | Service-to-database credentials are static passwords (`deploy/compose/docker-compose.yml`) |
| V2.10.2 | Fail | Default database credentials are used in Compose and CI (`deploy/compose/docker-compose.yml`) |
| V2.10.3 | Fail | Service passwords are plain environment variables; no protected store |
| V2.10.4 | Fail | The hard-coded fallback master key was removed (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) and `tools/secrets_scan.py` runs in CI, but secrets come from environment variables, not a secrets manager |
| V3.1.1 | Pass | Tokens are accepted only in the Authorization header (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.2.1 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.2.2 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.2.3 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.2.4 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.3.1 | N/A | Logout and token expiry are at the IdP; the API rejects expired JWTs (PyJWT `exp` check in `services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.3.2 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.3.3 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.3.4 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.4.1 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.4.2 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.4.3 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.4.4 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.4.5 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.5.1 | N/A | No server-side sessions or cookies; the API is stateless with OIDC bearer tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.5.2 | Fail | A static dev token exists for local and CI runs; it is disabled in Helm (`tests/unit/test_dev_auth_guard.py`) but present in the code base |
| V3.5.3 | Pass | JWTs are RS256-signed and checked for issuer, audience and expiry (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V3.7.1 | Fail | No step-up or re-authentication before sensitive actions such as deletion requests |
| V4.1.1 | Pass | Cedar and RLS enforce on the server (`policies/cedar/authz.cedar`, `tests/integration/test_rls_and_bitemporal.py`) |
| V4.1.2 | Pass | Tenant and roles come only from signed token claims; dev headers apply only to the dev token (`tests/unit/test_dev_auth_guard.py`) |
| V4.1.3 | Pass | Role matrix tests least privilege per action (`tests/unit/test_cedar_role_matrix.py`, `tests/trl5/test_t06_audit_slice.py`) |
| V4.1.5 | Pass | Missing auth context or Cedar errors deny (401/403) (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V4.2.1 | Pass | RLS on tenant tables and tenant checks on the in-memory report, assessment job and connector stores (`tests/integration/test_t29_pooled_leak.py`, `tests/trl5/test_t21_multi_tenant.py`, `tests/unit/test_security_hardening.py`) |
| V4.2.2 | N/A | Bearer tokens in headers, no cookies, so CSRF does not apply (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V4.3.1 | N/A | No separate administrative interface; MFA is configured at the IdP |
| V4.3.2 | Pass | No static file or directory serving in the API (`services/core-api/src/cleartrace_core_api/app.py`) |
| V4.3.3 | Fail | No step-up authentication; segregation of duties exists for reviewers only (`tests/trl5/test_t14_reviewer_workflow.py`) |
| V5.1.1 | Pass | Query parameters are typed single values in FastAPI handlers; repeated parameters do not merge (`services/core-api/src/cleartrace_core_api/routers/systems.py`) |
| V5.1.2 | Pass | Pydantic models list allowed fields; extra fields are not bound to records (`services/core-api/src/cleartrace_core_api/routers/`) |
| V5.1.3 | Pass | Typed request models with patterns and lengths, NUL rejection (`services/core-api/src/cleartrace_core_api/middleware/json_input_guard.py`), fuzzed by Schemathesis (`scripts/ci_security_suite.sh`) |
| V5.1.4 | Pass | Request schemas published in the served OpenAPI and checked for drift (`tests/unit/test_openapi_drift.py`) |
| V5.1.5 | N/A | The API issues no redirects |
| V5.2.1 | N/A | No HTML input is accepted |
| V5.2.2 | Pass | Free-text fields have length limits and NUL rejection (`services/core-api/src/cleartrace_core_api/data_policy/models.py`, `middleware/json_input_guard.py`) |
| V5.2.3 | N/A | No mail system integration |
| V5.2.4 | Pass | No eval; custom metrics run in a restricted CEL evaluator (`tests/unit/test_cel_evaluator.py`, `tests/trl5/test_t17_custom_metrics.py`) |
| V5.2.5 | Pass | Report templates are fixed server-side; user values are autoescaped (`services/reports/src/cleartrace_reports/`) |
| V5.2.6 | Pass | Webhook URLs must be https to public hosts (`services/notifier/src/cleartrace_notifier/webhook.py`); connectors go through the egress proxy (`tests/trl5/test_ssrf_egress_proxy.py`, `tests/unit/test_security_hardening.py`) |
| V5.2.7 | N/A | No SVG upload is rendered |
| V5.2.8 | N/A | No user-supplied Markdown, CSS or template content is rendered |
| V5.3.1 | Pass | JSON and problem+json responses are encoded by the framework (`services/core-api/src/cleartrace_core_api/errors/problem.py`) |
| V5.3.2 | Pass | UTF-8 throughout; EN/FR content round-trips (`tests/trl5/test_t20_bilingual_ui.py`) |
| V5.3.3 | Pass | React escapes output by default (`web/app/`, `web/components/`); API sets CSP `default-src 'none'` (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V5.3.4 | Pass | All SQL uses driver parameters (`services/core-api/src/cleartrace_core_api/routers/systems.py`); Bandit B608 runs in CI (`.github/workflows/ci.yml`) |
| V5.3.5 | Pass | No string-built queries; Semgrep and Bandit run on every CI run (`scripts/ci_security_suite.sh`) |
| V5.3.6 | Pass | Request JSON is parsed by FastAPI/Pydantic (`services/core-api/src/cleartrace_core_api/routers/`); no eval, checked by Semgrep and Bandit (`scripts/ci_security_suite.sh`) |
| V5.3.7 | N/A | No LDAP |
| V5.3.8 | Pass | No shell invocation with user input in services; Bandit B602-B607 in CI (`.github/workflows/ci.yml`) |
| V5.3.9 | Pass | Pack slug and connector manifest names are pattern-checked and confined to their folders (`services/core-api/src/cleartrace_core_api/routers/assessments.py`, `routers/connectors.py`) |
| V5.3.10 | N/A | No XML or XPath processing |
| V5.4.1 | N/A | Python services; no manual memory management |
| V5.4.2 | Pass | Format strings are code literals (f-strings); no `%`/`.format` on request data, checked by Semgrep and Bandit (`scripts/ci_security_suite.sh`) |
| V5.4.3 | Pass | Integer fields have ranges (`services/core-api/src/cleartrace_core_api/data_policy/models.py`, `services/core-api/src/cleartrace_core_api/pagination.py`) |
| V5.5.1 | N/A | No serialized objects are exchanged with clients |
| V5.5.2 | N/A | No XML parsing |
| V5.5.3 | Pass | YAML is loaded with `yaml.safe_load` (`services/connectors/src/cleartrace_connectors/manifest.py`); JSON via Pydantic |
| V5.5.4 | Pass | The web shell parses JSON with `response.json()` (`web/lib/`) |
| V6.1.1 | Fail | Data-policy records are AES-GCM envelope-encrypted (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) but other tables and evidence bytes are not encrypted at rest |
| V6.1.2 | N/A | No health data is processed |
| V6.1.3 | N/A | No financial data is processed |
| V6.2.1 | Pass | AES-GCM from `cryptography` raises on tampering; no custom padding (`tests/unit/test_data_policy_crypto.py`) |
| V6.2.2 | Pass | `cryptography` AESGCM, SHA-256, HMAC-SHA256 only (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`, `services/notifier/src/cleartrace_notifier/webhook.py`) |
| V6.2.3 | Pass | AES-256-GCM with random 96-bit nonces (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) |
| V6.2.4 | Fail | Algorithms are hard-coded; no crypto agility or algorithm configuration |
| V6.2.5 | Pass | No ECB, PKCS#1 v1.5, 3DES or Blowfish in use (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) |
| V6.2.6 | Pass | Fresh `os.urandom(12)` nonce per encryption and per data key (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) |
| V6.3.1 | Pass | Keys, nonces and token comparison use `os.urandom`, AESGCM.generate_key and `secrets` (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`, `auth/middleware.py`) |
| V6.3.2 | Fail | Identifiers are UUIDv7 (time-ordered), not UUIDv4; they are not used as secrets |
| V6.4.1 | Fail | No secrets manager or key vault; secrets are environment variables |
| V6.4.2 | Fail | Key material is held in the application process (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) |
| V7.1.1 | Pass | Audit events record actor, action and resource, never tokens (`services/core-api/src/cleartrace_core_api/auth/middleware.py`, `services/audit/src/cleartrace_audit/`) |
| V7.1.2 | Pass | Audit payloads hold identifiers and actions, not personal data (`tests/trl5/test_t06_audit_slice.py`) |
| V7.1.3 | Fail | Authorization denials are audited (`tests/trl5/test_t06_audit_slice.py`) but authentication failures and validation failures are not logged |
| V7.1.4 | Pass | Audit rows carry tenant, actor, action, resource and timestamp (`db/migrations/versions/0001_initial_schema.py`) |
| V7.2.1 | Fail | Failed token validations return 401 without a log or audit event (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V7.2.2 | Pass | Every Cedar denial is written to the audit ledger (`tests/trl5/test_t06_audit_slice.py`) |
| V7.3.1 | Pass | Audit events are canonical JSON, so values cannot forge entries (`services/audit/src/cleartrace_audit/canonical.py`) |
| V7.3.3 | Pass | Hash-chained, checkpointed audit ledger with tamper detection (`tests/trl5/test_t23_audit_tamper.py`) |
| V7.3.4 | Pass | Timestamps are timezone-aware UTC (`timestamptz`) (`db/migrations/versions/0001_initial_schema.py`) |
| V7.4.1 | Pass | Errors return generic RFC 9457 problem+json; token errors return a fixed message (`services/core-api/src/cleartrace_core_api/errors/handlers.py`, `auth/middleware.py`) |
| V7.4.2 | Pass | Exception handlers for HTTP and validation errors (`services/core-api/src/cleartrace_core_api/errors/handlers.py`) |
| V7.4.3 | Fail | No explicit last-resort handler; unhandled exceptions fall to Starlette's default 500 |
| V8.1.1 | Pass | `Cache-Control: no-store` on API responses (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V8.1.2 | Fail | Reports and idempotency records are kept in process memory without expiry (`services/core-api/src/cleartrace_core_api/routers/reports.py`, `routers/systems.py`) |
| V8.1.3 | Pass | Requests carry only the bearer token and documented headers (`api/openapi.yaml`) |
| V8.1.4 | Fail | Per-tenant rate limiting returns 429 (`tests/trl5/test_t21_multi_tenant.py`) but there is no alerting on abnormal request volume |
| V8.2.1 | Pass | `Cache-Control: no-store` set on all API responses (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V8.2.2 | Pass | Browser storage holds only the locale preference (`web/lib/hooks/useLocale.ts`, `web/components/I18nApp.tsx`) |
| V8.2.3 | N/A | The TRL 5 web shell has no sign-in and holds no authenticated data (`web/lib/`) |
| V8.3.1 | Pass | Sensitive values travel in headers or bodies; query strings carry ids, filters and cursors only (`api/openapi.yaml`) |
| V8.3.2 | Fail | Deletion requests exist (`tests/integration/test_t07_deletion.py`) but there is no user data export on demand |
| V8.3.3 | N/A | Users are government staff provisioned through the IdP; personal-data consent is handled by the deploying department |
| V8.3.4 | Fail | Classification exists (`db/migrations/versions/0601_data_policy.py`) but no full sensitive-data inventory |
| V8.3.5 | Pass | Privileged reads are audited (`tests/trl5/test_t06_audit_slice.py`) |
| V8.3.6 | Fail | Python cannot reliably zero memory; not addressed |
| V8.3.7 | Pass | AES-GCM authenticated encryption for protected records (`services/core-api/src/cleartrace_core_api/data_policy/crypto.py`) |
| V8.3.8 | Pass | Retention rules and certified deletion (`tests/integration/test_t07_deletion.py`) |
| V9.1.1 | Pass | Client traffic terminates TLS at the Helm ingress when `cleartrace.ingress.tls` names a certificate secret (`deploy/helm/cleartrace/templates/ingress.yaml`, `deploy/helm/cleartrace/values.yaml`); the API also sends HSTS (`middleware/security_headers.py`). Plain-HTTP fallback is left to the ingress controller, and the default values ship with `tls: []` |
| V9.1.2 | Fail | Client TLS terminates at the Helm ingress (`deploy/helm/cleartrace/templates/ingress.yaml`), but the chart sets no protocol or cipher-suite policy and no TLS scanner has been run against a deployment, so strong-cipher-only cannot be shown |
| V9.1.3 | Fail | No TLS protocol configuration in the shipped deployment |
| V9.2.1 | Fail | No certificates configured between components |
| V9.2.2 | Fail | Only the PgBouncer to Postgres hop can be encrypted (`deploy/compose/docker-compose.tls.yml`); API to PgBouncer, NATS and OPA connections are plaintext (`deploy/compose/docker-compose.yml`) |
| V9.2.3 | Pass | Outbound webhooks are https only and HMAC-signed (`services/notifier/src/cleartrace_notifier/webhook.py`) |
| V9.2.4 | Fail | No OCSP stapling or revocation checking configured |
| V10.2.1 | Pass | No telemetry or phone-home; OPA is started with `--disable-telemetry`, Semgrep with `--metrics off` (`scripts/ci_security_suite.sh`) |
| V10.2.2 | N/A | Server application; no device permissions |
| V10.3.1 | N/A | No auto-update feature |
| V10.3.2 | Fail | No code signing of images or packages (cosign pending) |
| V10.3.3 | N/A | No DNS records are managed by the application |
| V11.1.1 | Pass | Reviewer workflow enforces state order and rejects stale steps with 409 (`tests/trl5/test_t14_reviewer_workflow.py`) |
| V11.1.2 | Fail | No realistic-time checks on business flows |
| V11.1.3 | Fail | Limits are per tenant (`services/core-api/src/cleartrace_core_api/middleware/tenant_rate_limit.py`), not per user |
| V11.1.4 | Pass | Per-tenant rate limit returns 429 (`tests/trl5/test_t21_multi_tenant.py`) |
| V11.1.5 | Fail | No threat-model-derived business limits |
| V11.1.6 | Pass | Optimistic locking with If-Match (409 on missing or stale ETag) and stale reviewer actions rejected (`services/core-api/src/cleartrace_core_api/routers/systems.py`, `tests/trl5/test_t14_reviewer_workflow.py`) |
| V11.1.7 | Fail | No business-logic anomaly monitoring |
| V11.1.8 | Fail | No configurable alerting on automated attacks |
| V12.1.1 | Pass | Evidence uploads are capped at 25 MiB with 413 (`services/core-api/src/cleartrace_core_api/routers/evidence.py`) |
| V12.1.2 | N/A | Compressed uploads are stored as opaque bytes, never decompressed |
| V12.1.3 | Fail | No per-user file count or storage quota |
| V12.2.1 | Fail | Upload type is taken from the client Content-Type; content is not inspected (`services/core-api/src/cleartrace_core_api/routers/evidence.py`) |
| V12.3.1 | Pass | Uploaded file names are not used for storage; evidence is stored in the database by id (`services/evidence/src/cleartrace_evidence/store.py`) |
| V12.3.2 | Pass | Path inputs (pack slug, connector manifest) are pattern-checked and confined (`services/core-api/src/cleartrace_core_api/routers/assessments.py`, `routers/connectors.py`) |
| V12.3.3 | Pass | The uploaded filename is not read; evidence is stored by id in the database (`services/core-api/src/cleartrace_core_api/routers/evidence.py`, `services/evidence/src/cleartrace_evidence/store.py`) |
| V12.3.4 | Pass | Report downloads use a server-generated filename with `Content-Disposition: attachment` (`services/core-api/src/cleartrace_core_api/routers/reports.py`) |
| V12.3.5 | Pass | Upload metadata is stored as data and never reaches OS commands (`services/core-api/src/cleartrace_core_api/routers/evidence.py`) |
| V12.3.6 | Pass | No code loaded from untrusted sources; dependencies are locked in `uv.lock` |
| V12.4.1 | Pass | Uploads go to the database, not a web root (`services/evidence/src/cleartrace_evidence/store.py`) |
| V12.4.2 | Fail | No antivirus scanning of uploads |
| V12.5.1 | N/A | The API serves no static files |
| V12.5.2 | Pass | Uploaded evidence is never served as HTML; API CSP is `default-src 'none'` (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V12.6.1 | Pass | Connector egress goes through allow-listed profiles (`services/connectors/src/cleartrace_connectors/egress_profiles.py`, `tests/trl5/test_ssrf_egress_proxy.py`) |
| V13.1.1 | Pass | One framework (FastAPI/Starlette) and one JSON parser across the API (`services/core-api/src/cleartrace_core_api/app.py`) |
| V13.1.3 | Pass | Tokens are never in URLs (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
| V13.1.4 | Pass | Route-level Cedar checks plus row-level security (`tests/unit/test_cedar_role_matrix.py`, `tests/integration/test_rls_and_bitemporal.py`) |
| V13.1.5 | Pass | Wrong content types are rejected with 422 by request validation; covered by Schemathesis negative cases (`scripts/ci_security_suite.sh`) |
| V13.2.1 | Pass | Methods per route are role-checked by Cedar; undeclared methods return 405 with an Allow header (`tests/unit/test_cedar_role_matrix.py`, `services/core-api/src/cleartrace_core_api/errors/handlers.py`) |
| V13.2.2 | Pass | Pydantic schema validation before handlers run (`services/core-api/src/cleartrace_core_api/routers/`) |
| V13.2.3 | N/A | No cookies are used |
| V13.2.5 | Fail | JSON routes rely on body validation; Content-Type is not explicitly checked (415 is not returned) |
| V13.2.6 | Fail | TLS is not enforced (see V9.1.1); webhooks are signed, API requests are not |
| V13.3.1 | N/A | No XML or SOAP services |
| V13.3.2 | N/A | No SOAP services |
| V13.4.1 | N/A | No GraphQL |
| V13.4.2 | N/A | No GraphQL |
| V14.1.1 | Pass | CI builds and checks every candidate (`.github/workflows/ci.yml`) |
| V14.1.2 | N/A | Python services; no compiled native code is built |
| V14.1.3 | Fail | Helm sets no securityContext, resource limits or network policy (`deploy/helm/cleartrace/templates/deployment.yaml`) |
| V14.1.4 | Pass | Compose and Helm deployments are scripted (`deploy/compose/docker-compose.yml`, `deploy/helm/cleartrace/`) |
| V14.2.1 | Pass | Trivy fails on fixable critical/high issues (`.github/workflows/ci.yml`) |
| V14.2.2 | Fail | Demo dossiers are seeded by the interop export routes (`services/core-api/src/cleartrace_core_api/routers/interop.py`) and API docs are always on |
| V14.2.3 | Pass | No externally hosted assets: Swagger UI JS, CSS and favicon are vendored and served same-origin under the API docs mount (`services/core-api/static/swagger-ui/`, `services/core-api/src/cleartrace_core_api/app.py`), and the docs CSP allows no external host (`middleware/security_headers.py`) |
| V14.2.4 | Pass | Dependencies from PyPI and npm, locked (`uv.lock`, `web/package-lock.json`) and licence-gated (`tools/licence_gate.py`) |
| V14.2.5 | Pass | CycloneDX SBOM in CI (`.github/workflows/ci.yml`, `tests/trl5/test_t28_sbom.py`) |
| V14.2.6 | Fail | Third-party libraries are not sandboxed or encapsulated |
| V14.3.2 | Pass | No debug mode; uvicorn runs without reload or debug (`services/core-api/src/cleartrace_core_api/main.py`) |
| V14.3.3 | Pass | uvicorn runs with `server_header=False`; no version headers (`services/core-api/src/cleartrace_core_api/main.py`) |
| V14.4.1 | Pass | All API responses are JSON or problem+json with charset, or a declared report type (`services/core-api/src/cleartrace_core_api/errors/problem.py`) |
| V14.4.2 | Fail | Only report downloads carry `Content-Disposition: attachment`; JSON API responses do not |
| V14.4.3 | Pass | CSP `default-src 'none'; frame-ancestors 'none'` on API responses (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V14.4.4 | Pass | `X-Content-Type-Options: nosniff` on all responses (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V14.4.5 | Pass | `Strict-Transport-Security` on all responses (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V14.4.6 | Pass | `Referrer-Policy: no-referrer` (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V14.4.7 | Pass | `X-Frame-Options: DENY` and `frame-ancestors 'none'` (`services/core-api/src/cleartrace_core_api/middleware/security_headers.py`) |
| V14.5.1 | Fail | Undeclared methods return 405 with Allow, but they are not logged or alerted |
| V14.5.2 | Pass | Origin is used only by CORS, never for access decisions (`services/core-api/src/cleartrace_core_api/app.py`) |
| V14.5.3 | Pass | CORS uses an explicit origin allow-list from settings (`services/core-api/src/cleartrace_core_api/config.py`) |
| V14.5.4 | Pass | Bearer tokens are verified by signature on every request (`services/core-api/src/cleartrace_core_api/auth/middleware.py`) |
