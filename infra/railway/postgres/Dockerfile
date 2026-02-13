# Custom Postgres 17 with pgvector + PostGIS for Railway
# Deploy as a Railway service from this Dockerfile (not a template).
# Attach a persistent volume at /var/lib/postgresql/data.
FROM postgis/postgis:17-3.5

# pgvector — semantic search embeddings
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-17-pgvector && \
    rm -rf /var/lib/apt/lists/*

# Auto-enable extensions on every new database created by initdb
COPY initdb-extensions.sql /docker-entrypoint-initdb.d/10-extensions.sql

EXPOSE 5432
