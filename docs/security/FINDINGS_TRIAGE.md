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
| schemathesis | ST205 missing Allow header on 405 | medium | fixed | 405 responses now carry an Allow header built from the OpenAPI paths (`errors/handlers.py`), tested by `test_405_lists_every_documented_method`. |
| schemathesis | ST204 POST to GET-only path answered 400 | medium | fixed | The idempotency middleware only applies where a POST route exists, so the router returns 405 (`test_post_to_get_only_system_path_is_405_not_400`). |
| schemathesis | ST201 boolean accepted as integer or number | medium | fixed | Retention days and risk observations now reject booleans (strict fields and a before-validator in `data_policy/models.py`, `routers/risk.py`). |
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
| schemathesis | ST202 schema-valid strings with NUL rejected (about 13 POST/PUT operations) | medium | open | The OpenAPI string schemas allow U+0000, but the API rejects NUL with 422 on purpose because PostgreSQL text cannot store it. The rejection is safe; the schema should add a no-NUL pattern. |
| schemathesis | ST202 GET /systems opaque cursor rejected | medium | open | Cursors are opaque tokens issued by the API; arbitrary strings that are not one of them get a 400 problem response. The schema cannot express "issued by us", so this stays open as a contract gap, not a defect. |
| schemathesis | ST202 POST /assessments unknown control and POST /frameworks/assignments exactly-one rule | medium | open | Business rules (the control must exist in the framework; exactly one of ai_system_id or group_id) are enforced in code with 400 but are not expressed in the request schema. |
| schemathesis | ST202 POST /evidence multipart artefact_class | medium | open | The multipart form schema does not mark artefact_class as required while the endpoint requires it and returns 422. The OpenAPI document needs the form field marked required. |
| schemathesis | ST202 POST /webhooks private or host-less URLs | medium | open | Schema-valid https URLs that point to private, loopback or link-local addresses are refused with 422 by the SSRF guard. This is the intended security behaviour and cannot be expressed in a regex. |
| schemathesis | ST202 PATCH /systems If-Match and stateful run 412 | medium | open | PATCH requires the current ETag in If-Match (428 when missing, 412 when stale). Generated requests carry no or random ETags, so they are refused as designed. |
| schemathesis | ST202 POST /systems whitespace Idempotency-Key | medium | open | Keys made only of spaces arrive empty after HTTP header trimming. The schema now requires 1 to 128 visible ASCII characters; this row stays open until a CI run shows it gone. |
