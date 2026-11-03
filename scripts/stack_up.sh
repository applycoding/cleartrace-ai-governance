#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/deploy/compose/docker-compose.yml"
if command -v docker >/dev/null 2>&1; then
  bash "$ROOT/scripts/ci_compose_stack.sh"
  docker compose -f "$COMPOSE_FILE" up -d nats seaweedfs keycloak
else
  bash "$ROOT/scripts/dev_stack.sh"
fi
