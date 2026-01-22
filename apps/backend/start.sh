#!/bin/sh
set -e

echo "[STARTUP] Starting deployment script..."
echo "[STARTUP] Current directory: $(pwd)"
echo "[STARTUP] User: $(whoami)"

if [ -d "/data" ]; then
    mkdir -p /data/uploads/bugs || true
    chown -R 1001:1001 /data/uploads || true
fi

# Run migrations
echo "[STARTUP] Running database migrations..."
# Use the full path to ensure we find the executable, though PATH should handle it
if ! su fastapi -s /bin/sh -c "alembic upgrade head"; then
    echo "[STARTUP] ERROR: Migrations failed!"
    exit 1
fi
echo "[STARTUP] Migrations completed successfully."

# Start application
echo "[STARTUP] Starting Uvicorn server..."
exec su fastapi -s /bin/sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4"
