#!/bin/sh
set -e

echo "[STARTUP] Starting deployment script..."
echo "[STARTUP] Current directory: $(pwd)"
echo "[STARTUP] User: $(whoami)"

# Run migrations
echo "[STARTUP] Running database migrations..."
# Use the full path to ensure we find the executable, though PATH should handle it
if ! alembic upgrade head; then
    echo "[STARTUP] ERROR: Migrations failed!"
    exit 1
fi
echo "[STARTUP] Migrations completed successfully."

# Start application
echo "[STARTUP] Starting Uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4
