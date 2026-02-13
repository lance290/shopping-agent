-- Auto-enable extensions on database initialization.
-- This runs once when the data directory is first created by initdb.
-- For existing databases (restored via pg_dump), run these manually.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy text search (bonus)
