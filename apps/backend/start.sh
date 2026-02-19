#!/bin/sh
set -e

echo "[STARTUP] Starting deployment script..."
echo "[STARTUP] Current directory: $(pwd)"
echo "[STARTUP] User: $(whoami)"

if [ -d "/data" ]; then
    mkdir -p /data/uploads/bugs || true
    chown -R 1001:1001 /data/uploads || true
fi

# Create base SQLModel tables if they don't exist (idempotent)
# This is critical for fresh DBs where init_db() doesn't run in production
echo "[STARTUP] Ensuring base tables exist (SQLModel create_all)..."
if ! su fastapi -s /bin/sh -c "python -c 'from database import init_db; import asyncio; asyncio.run(init_db())'"; then
    echo "[STARTUP] WARNING: Base table creation failed, but continuing startup."
fi

# Patch missing tables/columns (idempotent safety net)
echo "[STARTUP] Running schema fix (pre-migration)..."
if ! su fastapi -s /bin/sh -c "python scripts/fix_schema.py"; then
    echo "[STARTUP] WARNING: Schema fix failed, but continuing startup."
fi

# Determine if DB is fresh (no alembic_version rows) or existing
# Fresh DB: init_db already created all tables with current schema, so stamp heads
# Existing DB: run upgrade heads to apply pending migrations
echo "[STARTUP] Running database migrations..."
ALEMBIC_ROWS=$(su fastapi -s /bin/sh -c "python -c \"
import asyncio
from database import engine
from sqlalchemy import text
async def check():
    try:
        async with engine.begin() as conn:
            r = await conn.execute(text('SELECT COUNT(*) FROM alembic_version'))
            return r.scalar() or 0
    except:
        return 0
print(asyncio.run(check()))
\"" 2>/dev/null || echo "0")

echo "[STARTUP] Alembic version rows: $ALEMBIC_ROWS"

if [ "$ALEMBIC_ROWS" = "0" ]; then
    echo "[STARTUP] Fresh DB detected — stamping Alembic heads (tables already created by init_db)..."
    if su fastapi -s /bin/sh -c "alembic stamp heads 2>&1"; then
        echo "[STARTUP] Alembic heads stamped successfully."
    else
        echo "[STARTUP] WARNING: Alembic stamp failed, but continuing startup."
    fi
else
    echo "[STARTUP] Existing DB — running Alembic upgrade..."
    if su fastapi -s /bin/sh -c "alembic upgrade heads 2>&1"; then
        echo "[STARTUP] Migrations completed successfully."
    else
        echo "[STARTUP] WARNING: Migrations returned non-zero. Checking if DB is usable..."
        su fastapi -s /bin/sh -c "alembic current 2>&1" || true
        if su fastapi -s /bin/sh -c "python -c \"from database import engine; import asyncio; asyncio.run(engine.dispose())\"" 2>/dev/null; then
            echo "[STARTUP] DB connection OK — continuing despite migration warning."
        else
            echo "[STARTUP] ERROR: DB connection failed. Exiting."
            exit 1
        fi
    fi
fi

# Run schema fix again AFTER migrations (catch anything migrations missed)
echo "[STARTUP] Running schema fix (post-migration)..."
if ! su fastapi -s /bin/sh -c "python scripts/fix_schema.py"; then
    echo "[STARTUP] WARNING: Post-migration schema fix failed, but continuing startup."
fi

# Run seed script (early-adopter vendors from vendors.py)
echo "[STARTUP] Seeding vendor data..."
if ! su fastapi -s /bin/sh -c "python scripts/seed_vendors.py"; then
    echo "[STARTUP] WARNING: Vendor seeding failed, but continuing startup."
fi

# Run research seed script (full vendor directory from vendor-research.md)
echo "[STARTUP] Seeding research vendor data..."
if ! su fastapi -s /bin/sh -c "python scripts/seed_from_research.py"; then
    echo "[STARTUP] WARNING: Research vendor seeding failed, but continuing startup."
fi

# Generate vendor embeddings (incremental — only missing ones)
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "[STARTUP] Generating vendor embeddings (incremental)..."
    if ! su fastapi -s /bin/sh -c "python scripts/generate_embeddings.py"; then
        echo "[STARTUP] WARNING: Embedding generation failed, but continuing startup."
    fi
else
    echo "[STARTUP] OPENROUTER_API_KEY not set — skipping embedding generation."
fi

# Start application
echo "[STARTUP] Starting Uvicorn server..."
exec su fastapi -s /bin/sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4"
