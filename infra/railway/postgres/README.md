# Custom Postgres for Railway (pgvector + PostGIS)

Railway's managed Postgres does **not** ship pgvector or PostGIS.
This directory contains a Dockerfile that builds a Postgres 17 image with both extensions (plus `pg_trgm` for fuzzy text search).

## Deploy on Railway

1. **Create a new service** in your Railway project:
   - Click **+ New** → **Docker Image** (or "GitHub Repo" pointing at this directory).
   - Set the **Dockerfile path** to `infra/railway/postgres/Dockerfile`.
   - Or push this directory to a standalone repo / use Railway's "Deploy from Dockerfile" option.

2. **Attach a persistent volume** mounted at:
   ```
   /var/lib/postgresql/data
   ```

3. **Set environment variables** on the service:
   | Variable | Value |
   |---|---|
   | `POSTGRES_DB` | `railway` |
   | `POSTGRES_USER` | `postgres` |
   | `POSTGRES_PASSWORD` | *(generate a strong password)* |
   | `PGDATA` | `/var/lib/postgresql/data/pgdata` |

4. **Update `DATABASE_URL`** on your backend service to point to the new Postgres service's private hostname.

## Migrating data from managed Postgres

```bash
# 1. Dump from old managed Postgres (public URL)
pg_dump "$OLD_DATABASE_URL" --no-owner --no-acl -Fc -f backup.dump

# 2. Restore into new custom Postgres
pg_restore --no-owner --no-acl -d "$NEW_DATABASE_URL" backup.dump

# 3. Enable extensions on the restored database
psql "$NEW_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql "$NEW_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql "$NEW_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

## Adding more extensions

Edit `Dockerfile` and add another `apt-get install` line:
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-17-<extension-name> && \
    rm -rf /var/lib/apt/lists/*
```

Then add the `CREATE EXTENSION` line to `initdb-extensions.sql` for new databases.
