#!/bin/sh
set -e

echo "[STARTUP] Starting deployment script..."
echo "[STARTUP] Current directory: $(pwd)"
echo "[STARTUP] User: $(whoami)"

if [ -d "/data" ]; then
    mkdir -p /data/uploads/bugs || true
    chown -R 1001:1001 /data/uploads || true
fi

# Run migrations (non-fatal — DB may already be at head)
echo "[STARTUP] Running database migrations..."
echo "[STARTUP] Migration files present:"
ls -1 alembic/versions/*.py 2>/dev/null | wc -l
if su fastapi -s /bin/sh -c "alembic upgrade heads"; then
    echo "[STARTUP] Migrations completed successfully."
else
    echo "[STARTUP] WARNING: Migrations returned non-zero. Checking if DB is usable..."
    if su fastapi -s /bin/sh -c "python -c \"from database import engine; import asyncio; asyncio.run(engine.dispose())\"" 2>/dev/null; then
        echo "[STARTUP] DB connection OK — continuing despite migration warning."
    else
        echo "[STARTUP] ERROR: DB connection failed. Exiting."
        exit 1
    fi
fi

# Patch any missing columns (idempotent)
echo "[STARTUP] Running schema fix..."
if ! su fastapi -s /bin/sh -c "python scripts/fix_schema.py"; then
    echo "[STARTUP] WARNING: Schema fix failed, but continuing startup."
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
