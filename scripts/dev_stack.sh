#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${CLEARTRACE_PGDATA:-$ROOT/.data/postgres}"
PORT="${CLEARTRACE_PGPORT:-5432}"
BOUNCER_PORT="${CLEARTRACE_PGBOUNCER_PORT:-6432}"

if [[ -f "${HOME}/miniforge3/etc/profile.d/conda.sh" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniforge3/etc/profile.d/conda.sh"
  conda activate base >/dev/null 2>&1 || true
fi

export PATH="${HOME}/miniforge3/bin:${HOME}/.local/bin:${PATH}"
export LD_LIBRARY_PATH="${HOME}/miniforge3/lib:${LD_LIBRARY_PATH:-}"

mkdir -p "$DATA_DIR"

if [[ ! -f "$DATA_DIR/PG_VERSION" ]]; then
  initdb -D "$DATA_DIR" -U cleartrace_super --auth-local=trust --auth-host=scram-sha-256
  cat >> "$DATA_DIR/postgresql.conf" <<CONF
listen_addresses = '127.0.0.1'
port = ${PORT}
unix_socket_directories = '${DATA_DIR}'
CONF
  echo "host all all 127.0.0.1/32 trust" >> "$DATA_DIR/pg_hba.conf"
  sed -i 's/^host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' "$DATA_DIR/pg_hba.conf"
  pg_ctl -D "$DATA_DIR" -l "$DATA_DIR/postgres.log" start
  psql -h 127.0.0.1 -p "$PORT" -U cleartrace_super -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE DATABASE cleartrace OWNER cleartrace_super;
SQL
  psql -h 127.0.0.1 -p "$PORT" -U cleartrace_super -d cleartrace -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
SQL
  pg_ctl -D "$DATA_DIR" stop
fi

if ! pg_isready -h 127.0.0.1 -p "$PORT" >/dev/null 2>&1; then
  pg_ctl -D "$DATA_DIR" -l "$DATA_DIR/postgres.log" start
fi

export CLEARTRACE_DATABASE_URL="postgresql+psycopg://cleartrace_super@127.0.0.1:${PORT}/cleartrace"
(cd "$ROOT/db" && uv run alembic -c alembic.ini upgrade head)
psql -h 127.0.0.1 -p "$PORT" -U cleartrace_super -d cleartrace -v ON_ERROR_STOP=1 <<'SQL'
ALTER ROLE cleartrace_app WITH LOGIN PASSWORD 'cleartrace_app';
SQL

if command -v pgbouncer >/dev/null 2>&1; then
  BOUNCER_INI="$ROOT/.data/pgbouncer.ini"
  cat > "$BOUNCER_INI" <<INI
[databases]
cleartrace = host=127.0.0.1 port=${PORT} dbname=cleartrace user=cleartrace_app password=cleartrace_app

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = ${BOUNCER_PORT}
auth_type = plain
auth_file = ${ROOT}/.data/pgbouncer_users.txt
pool_mode = transaction
server_reset_query = DISCARD ALL
max_client_conn = 200
default_pool_size = 20
pidfile = ${ROOT}/.data/pgbouncer.pid
logfile = ${ROOT}/.data/pgbouncer.log
INI
  echo "\"cleartrace_app\" \"cleartrace_app\"" > "$ROOT/.data/pgbouncer_users.txt"
  pkill pgbouncer 2>/dev/null || true
  sleep 1
  pgbouncer -d "$BOUNCER_INI"
fi

echo "Postgres ready on ${PORT}; PgBouncer on ${BOUNCER_PORT} (if installed)."
