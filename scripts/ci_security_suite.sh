#!/usr/bin/env bash
# T-26 targeted security suite: SAST (Semgrep, Bandit), API fuzzing (Schemathesis)
# and DAST (OWASP ZAP API scan). The container/dependency scan is the Trivy CI step.
#
# Every tool writes its raw output to artifacts/t26/. The tools run to completion
# and the pass/fail decision is made afterwards by tools/t26_gate.py, which reads
# those outputs and fails on any open critical/high finding that has no entry in
# docs/security/FINDINGS_TRIAGE.md. Nothing is filtered out before the gate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ART="$ROOT/artifacts/t26"
mkdir -p "$ART"
cd "$ROOT"

API_PORT="${CLEARTRACE_T26_API_PORT:-8080}"
OPA_PORT="${CLEARTRACE_T26_OPA_PORT:-8181}"
# ZAP shares the host network; a fixed proxy port avoids the race in zap-api-scan's
# own free-port pick (run 41756667418: "Address already in use", ZAP never started).
ZAP_PORT="${CLEARTRACE_T26_ZAP_PORT:-8095}"
API_URL="http://127.0.0.1:${API_PORT}"

status=0
record() { echo "$1=$2" >>"$ART/exit_codes.txt"; }
: >"$ART/exit_codes.txt"

echo "Semgrep (OSS p/ci rules)..."
set +e
uv run semgrep scan --config p/ci --metrics off --json -o "$ART/semgrep.json" -q
record semgrep $?
echo "Bandit (Python SAST)..."
uv run bandit -r packages services db -f json -o "$ART/bandit.json" -q
record bandit $?
set -e

echo "Starting OPA and core-api for API fuzzing and DAST..."
OPA_BIN="${OPA_BIN:-$(command -v opa)}"
"$OPA_BIN" run --server --disable-telemetry --log-level error \
  --addr "127.0.0.1:${OPA_PORT}" policies/rego >"$ART/opa.log" 2>&1 &
OPA_PID=$!
export CLEARTRACE_OPA_URL="http://127.0.0.1:${OPA_PORT}"
export CLEARTRACE_DEV_SKIP_AUTH=true
export CLEARTRACE_DEV_AUTH_TOKEN="${CLEARTRACE_DEV_AUTH_TOKEN:-t26-security-suite-token}"
export CLEARTRACE_API_PORT="$API_PORT"
# Per-tenant throttling is exercised by T-21; lift it here so the fuzzer and
# scanner reach the handlers instead of collecting 429s.
export CLEARTRACE_TENANT_RATE_LIMIT_PER_WINDOW="${CLEARTRACE_TENANT_RATE_LIMIT_PER_WINDOW:-1000000}"
uv run cleartrace-api >"$ART/core-api.log" 2>&1 &
API_PID=$!
cleanup() {
  kill "$API_PID" "$OPA_PID" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -sf "$API_URL/api/v1/health" >/dev/null; then
    break
  fi
  sleep 1
done
curl -sf "$API_URL/api/v1/health" >/dev/null

AUTH="Authorization: Bearer ${CLEARTRACE_DEV_AUTH_TOKEN}"
ROLES="X-ClearTrace-Dev-Roles: tenant_admin"

# Fuzz the schema the running app serves (generated from the real request models);
# tests/unit/test_openapi_drift.py keeps api/openapi.yaml in step with it.
echo "Schemathesis API fuzzing (served OpenAPI, all checks)..."
set +e
uv run schemathesis run "$API_URL/api/v1/openapi.json" --url "$API_URL" \
  --checks all --max-examples=25 --workers 1 \
  --header "$AUTH" --header "$ROLES" \
  --report junit --report-junit-path "$ART/schemathesis.xml" \
  >"$ART/schemathesis.log" 2>&1
record schemathesis $?
tail -n 60 "$ART/schemathesis.log"
set -e

if command -v docker >/dev/null 2>&1; then
  echo "OWASP ZAP API scan (served OpenAPI)..."
  chmod 777 "$ART"
  set +e
  # ZAP_AUTH_HEADER* is ZAP's documented way to add a bearer token to every request;
  # the replacer rule adds the dev-mode role header.
  docker run --rm --network host -v "$ART:/zap/wrk:rw" \
    -e ZAP_AUTH_HEADER=Authorization \
    -e ZAP_AUTH_HEADER_VALUE="Bearer ${CLEARTRACE_DEV_AUTH_TOKEN}" \
    -e ZAP_AUTH_HEADER_SITE=127.0.0.1 \
    ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -P "$ZAP_PORT" \
    -t "$API_URL/api/v1/openapi.json" -f openapi \
    -r zap-report.html -J zap-report.json \
    -z "-config replacer.full_list(0).description=roles -config replacer.full_list(0).enabled=true -config replacer.full_list(0).matchtype=REQ_HEADER -config replacer.full_list(0).matchstr=X-ClearTrace-Dev-Roles -config replacer.full_list(0).regex=false -config replacer.full_list(0).replacement=tenant_admin" \
    >"$ART/zap.log" 2>&1
  # zap-api-scan exits 1 on FAIL-level alerts and 2 on WARN-level alerts; the gate
  # reads riskcode from zap-report.json instead of trusting the exit code alone.
  record zap $?
  set -e
  tail -n 40 "$ART/zap.log"
else
  echo "docker not available: ZAP not run" | tee "$ART/zap.log"
  record zap missing
fi

cleanup
trap - EXIT

echo "T-26 gate..."
uv run python tools/t26_gate.py --artifacts "$ART" --triage docs/security/FINDINGS_TRIAGE.md \
  --summary "$ART/t26_summary.json" || status=$?
exit "$status"
