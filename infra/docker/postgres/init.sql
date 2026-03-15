-- ─────────────────────────────────────────────
--  EduSentinel – PostgreSQL Initialisation
--  Runs once on first container start.
--  Alembic manages schema migrations after this.
-- ─────────────────────────────────────────────

-- Ensure the database exists (idempotent)
SELECT 'CREATE DATABASE edusentinel'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'edusentinel')\gexec

\connect edusentinel

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- trigram index for name search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- composite GIN indexes

-- Dedicated app schema (optional but keeps objects tidy)
CREATE SCHEMA IF NOT EXISTS app;

-- Set default search path for the app user
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = current_user) THEN
    EXECUTE format('ALTER ROLE %I SET search_path TO app, public', current_user);
  END IF;
END
$$;
