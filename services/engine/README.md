# ClearTrace assessment engine

OPA Rego bundles under `policies/rego/` (digest via `bundle_digest`), **cel-python** applicability (Apache-2.0, blueprint §6.1 limits), five-state reducer (blueprint §6.2), EN/FR explanation templates, and certainty index v0.

The engine queries an OPA server over its Data API (`CLEARTRACE_OPA_URL`, default `http://127.0.0.1:8181`); it never starts processes itself. Run one with `opa run --server policies/rego`.

Install OPA for tests: `bash scripts/install_opa.sh` (pinned v1.4.2, SHA-256 checked; set `OPA_BIN` if not on `PATH`). The `opa_server` test fixture in `tests/conftest.py` starts a real OPA server for T-08, T-09 and T-13, and the tests fail if OPA is missing.

Used by TRL 5 tests T-08, T-09, T-11, and T-13.
