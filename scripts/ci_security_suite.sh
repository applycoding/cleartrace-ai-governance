#!/usr/bin/env bash
# T-26 targeted security suite (SAST, DAST, API fuzzing). Container scan is Trivy in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ART="$ROOT/artifacts/t26"
mkdir -p "$ART"

cd "$ROOT"

echo "Semgrep (OSS rules)..."
uv run semgrep scan --config p/ci --metrics off --error --json -o "$ART/semgrep.json" || {
  code=$?
  echo "Semgrep reported findings (exit $code); see $ART/semgrep.json"
  exit "$code"
}

echo "Bandit (Python SAST)..."
uv run bandit -r packages services db -f json -o "$ART/bandit.json" -q || {
  code=$?
  echo "Bandit reported findings (exit $code)"
  exit "$code"
}

echo "Starting core-api for DAST/fuzzing..."
export CLEARTRACE_DEV_SKIP_AUTH=true
export CLEARTRACE_DEV_AUTH_TOKEN=t26-security-suite-token
export CLEARTRACE_DATABASE_URL="${CLEARTRACE_DATABASE_URL:-postgresql+psycopg://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace}"

uv run cleartrace-api &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8080/api/v1/health" >/dev/null; then
    break
  fi
  sleep 1
done
curl -sf "http://127.0.0.1:8080/api/v1/health" >/dev/null

echo "Schemathesis API fuzzing (OpenAPI)..."
uv run schemathesis run "$ROOT/api/openapi.yaml" --base-url "http://127.0.0.1:8080" \
  --checks all --max-examples=25 \
  --header "Authorization: Bearer t26-security-suite-token" \
  --report junit \
  --report-junit-path "$ART/schemathesis.xml"

echo "OWASP ZAP API scan (OpenAPI)..."
docker run --rm --network host -v "$ROOT/api:/zap/wrk/api:ro" -v "$ART:/zap/wrk/out" \
  ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py \
  -t "http://127.0.0.1:8080/api/v1/openapi.json" \
  -f openapi \
  -r "$ART/zap-report.html" \
  -J "$ART/zap-report.json" \
  -z "-config apiScan.maxDuration=10"

echo "T-26 security suite completed; artifacts in $ART"
