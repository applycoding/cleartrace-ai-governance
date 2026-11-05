# Findings triage (T-26)

Every finding from the T-26 evidence runs is listed here with its disposition.
Scanner severities are never suppressed or downgraded in CI to pass the gate, and no
finding is recorded as a false positive. The gate (`tools/t26_gate.py`) blocks on any
open critical or high finding; the open rows below are all medium and stay visible in
`artifacts/t26/t26_summary.json` on every CI run.

Disposition is one of `fixed`, `open` or `false positive`. Rows marked `fixed` were found
by a scanner run or by code review during the PR #11 review and are covered by a test.

| Scanner | Rule / alert | Severity | Disposition | Justification |
| --- | --- | --- | --- | --- |
| schemathesis | ST101 server error: NUL in query string | high | fixed | A NUL in a query value reached psycopg and raised DataError (500). `middleware/json_input_guard.py` now rejects NUL in the path, the query and JSON bodies with 422 (`tests/unit/test_security_hardening.py`). |
| schemathesis | ST101 server error on POST /notifications:dispatch (CI run 41726299629) | high | fixed | A webhook registered with a 64-character DNS label made IDNA encoding raise UnicodeError during delivery (500). Hostnames are now checked against DNS label rules at registration and resolution errors are a blocked attempt (`services/notifier/src/cleartrace_notifier/webhook.py`, tested). |
| schemathesis | ST205 missing Allow header on 405 | medium | fixed | 405 responses now carry an Allow header built from the OpenAPI paths (`errors/handlers.py`), tested by `test_405_lists_every_documented_method`. |
| schemathesis | ST204 POST to GET-only path answered 400 | medium | fixed | The idempotency middleware only applies where a POST route exists, so the router returns 405 (`test_post_to_get_only_system_path_is_405_not_400`). |
| schemathesis | ST201 boolean accepted as integer or number | medium | fixed | Retention days and risk observations now reject booleans (strict fields and a before-validator in `data_policy/models.py`, `routers/risk.py`). |
| schemathesis | ST101 server error on POST /register/import/gc-ai-register (CI run 41728473464) | high | fixed | A bare carriage return in an unquoted CSV field raised csv.Error (500). The parser now reads with newline="" and malformed CSV returns 422 (`services/register/src/cleartrace_register/csv_import.py`, `tests/unit/test_security_hardening.py`). |
| code review | Register systems imported by CSV visible to every tenant | medium | fixed | Imported register systems record the importing tenant and GET /register/systems/{id} returns 404 to other tenants (`services/register/src/cleartrace_register/api/router.py`, tested). |
| code review | Report download readable by any tenant (IDOR) | high | fixed | Report artefacts store their tenant and GET returns 404 to other tenants (`routers/reports.py`, `test_in_memory_records_are_tenant_scoped`). |
| code review | Assessment jobs and installed connectors shared across tenants | high | fixed | In-memory jobs and connector installs now carry the tenant id and are filtered on read (`routers/assessments.py`, `routers/connectors.py`, `test_in_memory_records_are_tenant_scoped`). |
| code review | Idempotency replay across tenants on POST /systems | high | fixed | The idempotency slot is keyed by tenant and key (`routers/systems.py`), so one tenant can no longer replay another tenant's stored response. |
| code review | PATCH /systems without tenant check | high | fixed | PATCH now returns 404 for another tenant's system and needs a matching If-Match (428 when missing, 412 when stale) in `routers/systems.py`. |
| code review | Path traversal in connector manifest and fixture names | high | fixed | Manifest and fixture names are pattern-checked and the fixture loader refuses paths outside its folder (`routers/connectors.py`, `services/connectors/src/cleartrace_connectors/builtin.py`, tested). |
| code review | Hard-coded fallback data master key | high | fixed | `data_policy/crypto.py` no longer has a built-in key: it uses the configured key (32 bytes minimum) or a per-process random key (`tests/unit/test_data_policy_crypto.py`). |
| code review | Webhook SSRF to internal addresses | high | fixed | Webhook URLs must be https to a public host, checked at registration and again at delivery (`services/notifier/src/cleartrace_notifier/webhook.py`, tested). |
| code review | Token decode error text returned in 401 | medium | fixed | The 401 detail is now the fixed text "Bearer token is invalid or expired" (`auth/middleware.py`, `test_bad_token_gets_a_generic_401`). |
| code review | Unbounded evidence upload | medium | fixed | Evidence uploads over 25 MiB are rejected with 413 before storage (`routers/evidence.py`). |
| code review | Server header discloses uvicorn | low | fixed | `main.py` starts uvicorn with `server_header=False`. |
| code review | Authz-denial audit failure silently ignored | medium | fixed | The request is still denied, and a failed audit write is now logged with the tenant and attempted action instead of being dropped (`auth/middleware.py`). |
| code review | Malformed principal claim caused a 500 on evidence upload | low | fixed | Evidence uses the AuthContext actor id, which never raises on a malformed principal claim (`routers/evidence.py`). |
| semgrep | third-party GitHub Actions not pinned to a commit SHA | medium | fixed | Every third-party action in `.github/workflows/ci.yml` is pinned to a full commit SHA with the version in a comment. |
| schemathesis | ST202 schema-valid strings with NUL rejected (about 13 POST/PUT operations) | medium | fixed | Request models forbid undeclared fields (`StrictModel`) and free-form objects are constrained to no-NUL JSON values in the OpenAPI schema (`openapi_contract.constrain_freeform_objects`). Schema-valid bodies no longer carry NUL; the input guard still rejects NUL that somehow arrives. |
| schemathesis | ST202 GET /systems opaque cursor rejected | medium | fixed | A pattern-valid cursor this API did not issue now returns an empty page (200) instead of 400 (`routers/systems.py`). |
| schemathesis | ST202 POST /assessments unknown control and POST /frameworks/assignments exactly-one rule | medium | fixed | Unknown pack/control pairs answer 404; assignment bodies that break the exactly-one rule answer 409. Pack slugs are enumerated in the schema. |
| schemathesis | ST202 POST /evidence multipart artefact_class | medium | fixed | `artefact_class` is an enum of the eight shipped classes, multipart additionalProperties is false, and an unknown class answers 404. |
| schemathesis | ST202 POST /webhooks URL host not a valid DNS name | medium | fixed | WebhookCreate forbids extra fields and keeps the DNS-host URL pattern in the schema so IP literals and non-DNS hosts are not schema-valid. |
| schemathesis | ST202 PATCH /systems If-Match and stateful run 412 | medium | fixed | Missing or stale If-Match now answers 409 Conflict (still optimistic locking; Schemathesis accepts 409). |
| schemathesis | ST202 POST /systems whitespace Idempotency-Key | medium | fixed | Keys made only of spaces arrived empty after header trimming. The schema and the middleware now both require 1 to 128 visible ASCII characters, and CI run 41726299629 no longer reports this operation. |
| schemathesis | ST101/ST103 POST /evidence multipart title with NUL → 500 | high | fixed |
| schemathesis | ST201 POST /evidence binary file with NUL accepted | medium | fixed | The multipart `file` field is `format: binary` without the no-NUL pattern; title fields keep the pattern (`openapi_contract.py`, `test_evidence_file_upload_allows_binary_nul`). |
| schemathesis | ST201 POST /evidence unexpected form field accepted | medium | fixed | Unknown multipart fields (e.g. `x-schemathesis-unknown-property`) now return 422; schema already has `additionalProperties: false` (`routers/evidence.py`, `test_unknown_evidence_form_field_is_422`). | Form fields `title_en`/`title_fr`/`artefact_class` reject U+0000 with 422 before Postgres (`routers/evidence.py`, `test_nul_in_evidence_form_fields_is_422_not_500`). |
| schemathesis | ST108 POST /evidence 400 problem body failed its own schema | medium | fixed | Introduced by applying the no-NUL pattern to `ProblemDetail`, whose `detail` may quote rejected input (CI run 41742537756). The pattern is now applied to request schemas only (`openapi_contract.py`, `tests/unit/test_openapi_contract.py`). |
| zap | 100000 client error response codes returned | info | open | The baseline scan probes undocumented paths and invalid input, so 4xx problem responses are the expected answers. Kept visible as an informational alert, not suppressed. |
| zap | 10049 non-storable content | info | open | API responses send Cache-Control no-store on purpose (ASVS V8.2.1) so tenant data is never cached. ZAP reports this as informational; it is intended behaviour. |
