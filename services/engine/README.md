# ClearTrace assessment engine

OPA Rego bundles under `policies/rego/` (digest via `bundle_digest`), **cel-python** applicability (Apache-2.0, blueprint §6.1 limits), five-state reducer (blueprint §6.2), EN/FR explanation templates, and certainty index v0.

Install OPA for tests: `bash scripts/install_opa.sh` (set `OPA_BIN` if not on `PATH`).

Used by TRL 5 tests T-08, T-09, T-11, and T-13.
