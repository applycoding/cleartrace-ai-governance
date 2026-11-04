#!/usr/bin/env bash
# CycloneDX SBOMs for every image the product ships or deploys (Syft, Apache-2.0).
# Images that cannot be pulled are recorded as not scanned, with the reason, so the
# licence report never treats a missing scan as a clean one.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/artifacts/image-sbom"
SYFT_VERSION="1.18.1"
SYFT_SHA256="066c251652221e4d44fcc4d115ce3df33a91769da38c830a8533199db2f65aab"
mkdir -p "${OUT}"

if ! command -v syft >/dev/null 2>&1; then
  tmp="$(mktemp -d)"
  curl -sSfL -o "${tmp}/syft.tgz" \
    "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_linux_amd64.tar.gz"
  echo "${SYFT_SHA256}  ${tmp}/syft.tgz" | sha256sum -c -
  tar -xzf "${tmp}/syft.tgz" -C "${tmp}" syft
  sudo install -m 0755 "${tmp}/syft" /usr/local/bin/syft
fi

cd "${ROOT}"
mapfile -t REFS < <(uv run python tools/image_licence_report.py --list-images)

status="${OUT}/scan_status.tsv"
: > "${status}"
for ref in "${REFS[@]}"; do
  safe="$(echo "${ref}" | tr '/:@' '___')"
  echo "Syft scan ${ref}"
  if syft "registry:${ref}" -q -o cyclonedx-json > "${OUT}/${safe}.json" 2> "${OUT}/${safe}.err"; then
    printf '%s\tscanned\t%s.json\n' "${ref}" "${safe}" >> "${status}"
  else
    rm -f "${OUT}/${safe}.json"
    printf '%s\tnot_scanned\t%s\n' "${ref}" "$(tail -n 1 "${OUT}/${safe}.err" | tr '\t' ' ' | cut -c1-300)" >> "${status}"
  fi
done

uv run python tools/image_licence_report.py
