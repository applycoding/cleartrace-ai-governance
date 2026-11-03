#!/usr/bin/env bash
set -euo pipefail

OPA_VERSION="${OPA_VERSION:-1.4.2}"
INSTALL_DIR="${OPA_INSTALL_DIR:-/tmp/opa-install}"
mkdir -p "${INSTALL_DIR}"

ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64)
    OPA_ARCH=amd64
    DEFAULT_SHA256="2c0ccdbbe0b8e2a5d12d9c42d92f1f34f494ffb32d1f3c4ddc36101be637d66f"
    ;;
  aarch64 | arm64)
    OPA_ARCH=arm64
    DEFAULT_SHA256="facd6a9ea375c6299701f86b90b470e52305c5726c4f136e2980fa6123ae9613"
    ;;
  *)
    echo "Unsupported architecture: ${ARCH}" >&2
    exit 1
    ;;
esac

URL="https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${OPA_ARCH}_static"
curl -fsSL "${URL}" -o "${INSTALL_DIR}/opa"

# The pinned checksums are the published SHA-256 values for v1.4.2.
# Set OPA_SHA256 when installing another version.
if [[ "${OPA_VERSION}" == "1.4.2" ]]; then
  EXPECTED_SHA256="${OPA_SHA256:-${DEFAULT_SHA256}}"
else
  EXPECTED_SHA256="${OPA_SHA256:?Set OPA_SHA256 for OPA versions other than 1.4.2}"
fi
echo "${EXPECTED_SHA256}  ${INSTALL_DIR}/opa" | sha256sum --check --strict -
chmod +x "${INSTALL_DIR}/opa"
echo "Installed OPA v${OPA_VERSION} to ${INSTALL_DIR}/opa"
echo "Export OPA_BIN=${INSTALL_DIR}/opa for ClearTrace engine tests."
