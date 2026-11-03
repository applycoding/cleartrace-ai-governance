#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v docker >/dev/null 2>&1; then
  docker compose -f "$ROOT/deploy/compose/docker-compose.yml" up -d
else
  bash "$ROOT/scripts/dev_stack.sh"
fi
