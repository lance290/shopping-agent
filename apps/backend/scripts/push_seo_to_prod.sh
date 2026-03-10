#!/usr/bin/env bash
# push_seo_to_prod.sh
# Run after seo_enrich.py finishes.
# Dumps the enriched local vendor DB → gzip → pushes to Railway production.
#
# Usage:
#   cd apps/backend
#   bash scripts/push_seo_to_prod.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DUMP_JSON="$BACKEND_DIR/data/vendors_prod_dump.json"
DUMP_GZ="$BACKEND_DIR/data/vendors_prod_dump.json.gz"
PROD_BACKEND="https://backend-production-96ef.up.railway.app"
RESTORE_KEY="sh_restore_vendors_2026_secure_key"

cd "$BACKEND_DIR"
source .env 2>/dev/null || true

echo "=== Step 1: Count enriched vendors in local DB ==="
uv run python3 - <<'PY'
import asyncio
import os
import asyncpg

async def main():
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5437/shopping_agent?ssl=disable")
    conn = await asyncpg.connect(url)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM vendor")
        w_seo = await conn.fetchval("SELECT COUNT(*) FROM vendor WHERE seo_content IS NOT NULL")
        w_slug = await conn.fetchval("SELECT COUNT(*) FROM vendor WHERE slug IS NOT NULL")
        print(f"  total={total}  with_seo_content={w_seo}  with_slug={w_slug}")
    finally:
        await conn.close()

asyncio.run(main())
PY

echo ""
echo "=== Step 2: Dump local vendor table to JSON ==="
uv run python3 scripts/dump_vendors_async.py

echo ""
echo "=== Step 3: Compress to gzip ==="
gzip -f "$DUMP_JSON"
ls -lh "$DUMP_GZ"

echo ""
echo "=== Step 4: Push compressed dump to production ==="
HTTP_STATUS=$(curl -s -o /tmp/restore_response.json -w "%{http_code}" \
  -X POST "$PROD_BACKEND/admin/ops/restore-vendors" \
  -H "X-Restore-Key: $RESTORE_KEY" \
  -F "dump_file=@$DUMP_GZ;type=application/gzip")

echo "  HTTP status: $HTTP_STATUS"
cat /tmp/restore_response.json
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✅ Production restore complete."
else
  echo "❌ Production restore FAILED (HTTP $HTTP_STATUS). Check response above."
  exit 1
fi

echo ""
echo "=== Step 5: Spot-check a vendor page ==="
SLUG=$(uv run python3 - <<'PY'
import asyncio
import os
import asyncpg

async def main():
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5437/shopping_agent?ssl=disable")
    conn = await asyncpg.connect(url)
    try:
        row = await conn.fetchrow("SELECT slug FROM vendor WHERE slug IS NOT NULL LIMIT 1")
        print(row[0] if row else "")
    finally:
        await conn.close()

asyncio.run(main())
PY
)
if [ -n "$SLUG" ]; then
  echo "  Fetching https://frontend-production-1306.up.railway.app/vendors/$SLUG ..."
  curl -s -o /dev/null -w "  HTTP %{http_code} for /vendors/$SLUG\n" \
    "https://frontend-production-1306.up.railway.app/vendors/$SLUG"
fi

echo ""
echo "=== Done ==="
