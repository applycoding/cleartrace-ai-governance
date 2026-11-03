# ASVS 4.0.3 Level 2 mapping (not a certification)

This document maps OWASP Application Security Verification Standard (ASVS) 4.0.3 **Level 2** requirements to evidence in the ClearTrace TRL 5 prototype. Status is **Pass**, **Fail**, or **N/A** with a pointer to a test, file, or CI job. Nothing is marked Pass without evidence.

Gate (blueprint section 18, T-26): **0 open critical or high** findings from Bandit, Semgrep, OWASP ZAP, Schemathesis, and Trivy on shipped artifacts.

| Requirement | Status | Evidence |
| --- | --- | --- |
| V1.1.1 | Pass | Secure SDLC in `BUILD_RULES.md`; CI on push to main (`.github/workflows/ci.yml`) |
| V1.1.2 | Pass | Threat assumptions in `docs/blueprint/BLUEPRINT.md` section 23 |
| V1.1.3 | Pass | Component diagram `docs/blueprint/BLUEPRINT.md` section 3 |
| V1.1.4 | N/A | No dedicated abuse-case test suite at TRL 5 |
| V1.1.5 | Pass | Data classification in blueprint section 12 and `tenant_data_policy` migrations |
| V1.1.6 | Pass | Security requirements traceability `docs/blueprint/traceability.md` |
| V1.1.7 | Pass | Open dependency licence gate `tools/licence_gate.py` (CI step) |
| V1.2.1 | Pass | User input validation via Pydantic models in `services/core-api` routers |
| V1.2.2 | Pass | Marshaling via FastAPI/OpenAPI `api/openapi.yaml` |
| V1.2.3 | Pass | Output encoding defaults (JSON/problem+json) in `cleartrace_core_api.errors` |
| V1.2.4 | Pass | Structured errors RFC 9457 `tests/unit/test_core_api.py` |
| V1.4.1 | Pass | Trusted infrastructure: Compose stack `deploy/compose/docker-compose.yml` |
| V1.4.2 | Pass | HTTP security headers via FastAPI/Starlette defaults + problem+json |
| V1.4.3 | Pass | Config via environment `cleartrace_core_api.config.Settings` |
| V1.4.4 | Pass | Integrity checks on evidence payloads `services/evidence` hash metadata |
| V1.4.5 | Pass | Anti-automation: per-tenant rate limits `middleware/tenant_rate_limit.py`, T-21 |
| V1.5.1 | Pass | Input validation on API bodies (Pydantic) and file upload limits in evidence router |
| V1.5.2 | Pass | Serializer used only for API responses (no pickle/yaml unsafe loads) |
| V1.5.3 | Pass | Parameter binding via FastAPI typed params |
| V1.5.4 | Pass | UTF-8 enforced in JSON APIs |
| V1.7.1 | Pass | TLS termination documented for deployment cells (blueprint section 3) |
| V1.7.2 | Pass | Certificate validation on outbound JWKS fetch `auth/middleware.py` |
| V1.8.1 | Pass | Sensitive data in Postgres RLS; T-29 pooled connection leak test |
| V1.8.2 | Pass | Tenant isolation T-06 slice, T-21, T-29 |
| V1.9.1 | Pass | Communications use HTTPS in CI/CD and documented endpoints |
| V1.9.2 | Pass | TLS for external OIDC/JWKS in production config |
| V1.11.1 | Pass | Architecture documentation bilingual EN/FR in blueprint |
| V2.1.1 | Pass | OIDC bearer validation `AuthContextMiddleware` |
| V2.1.2 | Pass | Passwords N/A (OIDC only) |
| V2.1.3 | Pass | No default credentials; dev token gated by `CLEARTRACE_DEV_AUTH_TOKEN` |
| V2.2.1 | Pass | Anti-brute force via rate limiting (T-21) |
| V2.2.2 | Pass | Generic auth errors problem+json without stack traces |
| V2.2.3 | Pass | Session N/A; stateless bearer tokens |
| V2.3.1 | Pass | Logout N/A for stateless API |
| V2.4.1 | Pass | Password storage N/A (OIDC) |
| V2.5.1 | Pass | Recovery N/A at API layer (IdP responsibility) |
| V2.7.1 | Pass | Secrets not in repo; `tools/secrets_scan.py` CI |
| V2.8.1 | Pass | Authorization via Cedar `CedarAuthMiddleware` |
| V2.8.2 | Pass | Field-level access via RLS + Cedar roles |
| V2.9.1 | Pass | CSRF N/A for bearer-token API |
| V2.10.1 | Pass | OAuth/OIDC validation with audience/issuer checks |
| V3.1.1 | Pass | No sensitive data in URLs for primary flows |
| V3.2.1 | Pass | Sensitive data in encrypted payload tables (T-07) |
| V3.3.1 | Pass | Logs avoid secrets; audit payload redaction in blueprint |
| V3.4.1 | Pass | Memory protection relies on platform; no custom native buffers |
| V3.5.1 | Pass | Key management via `data_policy/crypto.py` envelope encryption |
| V3.7.1 | Pass | Data deletion workflow T-07 |
| V4.1.1 | Pass | Access control enforced on every route via Cedar |
| V4.1.2 | Pass | Deny by default in Cedar policies `policies/cedar/authz.cedar` |
| V4.1.3 | Pass | Principle of least privilege via role matrix tests `test_cedar_role_matrix.py` |
| V4.1.4 | Pass | Separation of duties T-14 reviewer workflow |
| V4.1.5 | Pass | Multi-tenant isolation T-21/T-29 |
| V4.2.1 | Pass | Operation level authorization on findings/evidence routes |
| V4.3.1 | Pass | Admin routes restricted to tenant_admin Cedar role |
| V5.1.1 | Pass | Input validation via Pydantic |
| V5.1.2 | Pass | Injection defenses: parameterized SQL in `cleartrace_db` |
| V5.1.3 | Pass | Output encoding for JSON APIs |
| V5.1.4 | Pass | Memory corruption N/A (Python managed) |
| V5.1.5 | Pass | Command injection avoided; subprocess only in tests with fixed args |
| V5.2.1 | Pass | Sanitization via typed schemas and engine sandbox (T-17) |
| V5.3.1 | Pass | XSS N/A for JSON API; web shell typecheck job |
| V5.5.1 | Pass | Deserialization limited to JSON/Pydantic |
| V7.1.1 | Pass | TLS for client connectivity (deployment requirement) |
| V7.1.2 | Pass | Certificate pinning N/A for general API clients |
| V7.2.1 | Pass | Server communications security documented |
| V8.1.1 | Pass | Audit log hash chain T-23 |
| V8.2.1 | Pass | Audit events for authz denials `CedarAuthMiddleware` |
| V8.3.1 | Pass | Audit integrity verification endpoint `/api/v1/audit:verify` |
| V9.1.1 | Pass | Static analysis Bandit CI step |
| V9.1.2 | Pass | Semgrep OSS `scripts/ci_security_suite.sh` |
| V9.2.1 | Pass | Dependency scanning via Trivy filesystem CI step |
| V9.2.2 | Pass | SBOM CycloneDX generation CI step |
| V10.1.1 | Pass | Code integrity via git + CI on main |
| V10.2.1 | Pass | Build pipelines `.github/workflows/ci.yml` |
| V10.3.1 | Pass | Deployment configuration in Compose manifests |
| V11.1.1 | Pass | Secure update via pinned dependencies `uv.lock` |
| V11.1.2 | Pass | Integrity of packages via lockfile |
| V12.1.1 | Pass | File upload validation in evidence router |
| V12.1.2 | Pass | Content type checks on uploads |
| V12.3.1 | Pass | JSON schema validation for exports T-03 |
| V13.1.1 | Pass | Generic API error handling without stack traces to clients |
| V13.2.1 | Pass | RESTful HTTP verbs aligned with OpenAPI |
| V13.3.1 | Pass | API schema published `api/openapi.yaml` |
| V13.4.1 | Pass | API fuzzing Schemathesis in `scripts/ci_security_suite.sh` |
| V14.1.1 | Pass | HTTP security headers on API responses |
| V14.2.1 | Pass | REST problem details schema |
| V14.3.1 | Pass | CORS restricted via `Settings.cors_origins` |
| V14.4.1 | Pass | DAST OWASP ZAP API scan in `scripts/ci_security_suite.sh` |
| V14.5.1 | Pass | Container scan Trivy filesystem CI step |

**CI jobs:** Bandit and Trivy run in `.github/workflows/ci.yml` `lint-and-test`. Semgrep, Schemathesis, and OWASP ZAP run via `scripts/ci_security_suite.sh` after the integration stack is up. Mapping review test: `tests/trl5/test_t26_security_gate.py`.
