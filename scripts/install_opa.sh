#!/usr/bin/env bash
set -euo pipefail

OPA_VERSION="${OPA_VERSION:-1.4.2}"
INSTALL_DIR="${OPA_INSTALL_DIR:-/tmp/opa-install}"
mkdir -p "${INSTALL_DIR}"

ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64) OPA_ARCH=amd64 ;;
  aarch64 | arm64) OPA_ARCH=arm64 ;;
  *)
    echo "Unsupported architecture: ${ARCH}" >&2
    exit 1
    ;;
esac

URL="https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_${OPA_ARCH}_static"
curl -fsSL "${URL}" -o "${INSTALL_DIR}/opa"
chmod +x "${INSTALL_DIR}/opa"
echo "Installed OPA v${OPA_VERSION} to ${INSTALL_DIR}/opa"
echo "Export OPA_BIN=${INSTALL_DIR}/opa for ClearTrace engine tests."
