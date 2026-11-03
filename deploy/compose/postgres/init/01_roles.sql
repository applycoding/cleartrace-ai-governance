-- Extensions for Docker Compose Postgres (pgvector image). Roles come from Alembic migrations.
CREATE EXTENSION IF NOT EXISTS vector;
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pgaudit;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'pgaudit unavailable';
END $$;
