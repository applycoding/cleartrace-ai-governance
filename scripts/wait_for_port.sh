#!/usr/bin/env bash
# Wait until host:port accepts TCP connections (used after PgBouncer/NATS restarts).
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:?port required}"
TRIES="${3:-60}"
SLEEP="${4:-1}"

for _ in $(seq 1 "$TRIES"); do
  if (echo >/dev/tcp/"$HOST"/"$PORT") 2>/dev/null; then
    exit 0
  fi
  sleep "$SLEEP"
done

echo "Timed out waiting for ${HOST}:${PORT}" >&2
exit 1
