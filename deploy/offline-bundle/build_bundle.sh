#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/deploy/offline-bundle/dist"
mkdir -p "$OUT"
cp "$ROOT/deploy/offline-bundle/images.manifest.json" "$OUT/"
cp "$ROOT/deploy/helm/cleartrace/Chart.yaml" "$OUT/chart-Chart.yaml"
if [[ -f "$ROOT/sbom.json" ]]; then
  cp "$ROOT/sbom.json" "$OUT/"
else
  uv run python "$ROOT/tools/sbom_builder.py"
  cp "$ROOT/sbom.json" "$OUT/"
fi
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"
echo "offline bundle staged in $OUT"
