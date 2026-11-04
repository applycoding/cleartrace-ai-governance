#!/usr/bin/env bash
# Generate CycloneDX SBOMs for shipped container images (CI only, Syft Apache-2.0).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/artifacts/image-sbom"
mkdir -p "${OUT}"

if ! command -v syft >/dev/null 2>&1; then
  curl -sSfL https://raw.githubusercontent.com/anchore/syft/v1.18.1/install.sh | sh -s -- -b /usr/local/bin
fi

mapfile -t REFS < <(
  python3 - <<'PY'
import json
from pathlib import Path
root = Path(".")
refs = set()
compose = root / "deploy/compose/docker-compose.yml"
for line in compose.read_text(encoding="utf-8").splitlines():
    if "image:" in line:
        refs.add(line.split("image:", 1)[1].strip())
manifest = root / "deploy/offline-bundle/images.manifest.json"
if manifest.exists():
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for item in data.get("images", []):
        refs.add(item["reference"])
for ref in sorted(refs):
    print(ref)
PY
)

cd "${ROOT}"
for ref in "${REFS[@]}"; do
  safe="$(echo "${ref}" | tr '/:@' '___')"
  echo "Syft scan ${ref}"
  syft "${ref}" -o cyclonedx-json > "${OUT}/${safe}.json"
done

echo "Wrote ${#REFS[@]} image SBOM files to ${OUT}"
