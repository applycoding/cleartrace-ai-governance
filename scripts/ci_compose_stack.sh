#!/usr/bin/env bash
# Start Postgres 16 (pgvector) and PgBouncer via Docker Compose for CI and local Docker dev.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT}/deploy/compose/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for ci_compose_stack.sh" >&2
  exit 1
fi

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

echo "Starting Postgres (Compose)..."
compose up -d postgres

echo "Waiting for Postgres health..."
for _ in $(seq 1 60); do
  if compose exec -T postgres pg_isready -U cleartrace_super -d cleartrace >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! compose exec -T postgres pg_isready -U cleartrace_super -d cleartrace >/dev/null 2>&1; then
  echo "Postgres did not become ready in time" >&2
  compose logs postgres
  exit 1
fi

export CLEARTRACE_DATABASE_URL="postgresql+psycopg://cleartrace_super:cleartrace_super@127.0.0.1:5432/cleartrace"
export CLEARTRACE_TEST_DSN="postgresql://cleartrace_app:cleartrace_app@127.0.0.1:6432/cleartrace"
export CLEARTRACE_CI=1

echo "Running Alembic migrations..."
(cd "$ROOT/db" && uv run alembic -c alembic.ini upgrade head)

echo "Starting PgBouncer (Compose)..."
compose up -d pgbouncer

echo "Waiting for PgBouncer on 6432..."
for _ in $(seq 1 60); do
  if (echo >/dev/tcp/127.0.0.1/6432) 2>/dev/null; then
    break
  fi
  sleep 1
done
if ! (echo >/dev/tcp/127.0.0.1/6432) 2>/dev/null; then
  echo "PgBouncer did not listen on 6432 in time" >&2
  compose logs pgbouncer
  exit 1
fi

echo "Integration stack ready (Postgres :5432, PgBouncer :6432)."
