-- Bootstrap roles for Docker Compose Postgres (pgvector image).
CREATE USER cleartrace_app WITH PASSWORD 'cleartrace_app' NOBYPASSRLS;
CREATE EXTENSION IF NOT EXISTS vector;
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pgaudit;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'pgaudit unavailable';
END $$;
