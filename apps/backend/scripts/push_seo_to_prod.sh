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
python3 - <<'PY'
import os
from sqlalchemy import create_engine, text
url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5437/shopping_agent").replace("+asyncpg","").replace("?ssl=disable","").replace("?sslmode=disable","")
e = create_engine(url + "?sslmode=disable")
with e.connect() as c:
    total  = c.execute(text("SELECT COUNT(*) FROM vendor")).scalar()
    w_seo  = c.execute(text("SELECT COUNT(*) FROM vendor WHERE seo_content IS NOT NULL")).scalar()
    w_slug = c.execute(text("SELECT COUNT(*) FROM vendor WHERE slug IS NOT NULL")).scalar()
    print(f"  total={total}  with_seo_content={w_seo}  with_slug={w_slug}")
PY

echo ""
echo "=== Step 2: Dump local vendor table to JSON ==="
python3 scripts/dump_vendors_async.py

echo ""
echo "=== Step 3: Compress to gzip ==="
gzip -f "$DUMP_JSON"
ls -lh "$DUMP_GZ"

echo ""
echo "=== Step 4: Push compressed dump to production ==="
HTTP_STATUS=$(curl -s -o /tmp/restore_response.json -w "%{http_code}" \
  -X POST "$PROD_BACKEND/admin/ops/restore-vendors" \
  -H "X-Restore-Key: $RESTORE_KEY" \
  -H "Content-Type: application/json")

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
SLUG=$(python3 - <<'PY'
import os
from sqlalchemy import create_engine, text
url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5437/shopping_agent").replace("+asyncpg","").replace("?ssl=disable","").replace("?sslmode=disable","")
e = create_engine(url + "?sslmode=disable")
with e.connect() as c:
    row = c.execute(text("SELECT slug FROM vendor WHERE slug IS NOT NULL LIMIT 1")).fetchone()
    print(row[0] if row else "")
PY
)
if [ -n "$SLUG" ]; then
  echo "  Fetching https://frontend-production-1306.up.railway.app/vendors/$SLUG ..."
  curl -s -o /dev/null -w "  HTTP %{http_code} for /vendors/$SLUG\n" \
    "https://frontend-production-1306.up.railway.app/vendors/$SLUG"
fi

echo ""
echo "=== Done ==="
