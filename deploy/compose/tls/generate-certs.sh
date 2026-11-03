#!/usr/bin/env bash
# Generate a self-signed Postgres TLS cert for local Compose (not for production).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$DIR"
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$DIR/server.key" \
  -out "$DIR/server.crt" \
  -days 825 \
  -subj "/CN=cleartrace-postgres"
chmod 600 "$DIR/server.key"
echo "Wrote $DIR/server.crt and server.key"
