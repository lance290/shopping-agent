# Syncing New CPG Brands to Production

The `cpg_outreach_enrich.py` script automatically runs locally, enriches data, saves it to the CSV, and creates `vendor` entries in your **local** database (including creating the `Vector(1536)` embeddings).

Since Railway production runs its own PostgreSQL database, you need to push these new local vendors to production once the script finishes.

### Steps to Sync

1. **Dump the local vendors to JSON:**
   Run the existing script to grab the newly enriched vendors from your local DB and compress them:
   ```bash
   cd apps/backend
   uv run python scripts/dump_vendors_async.py
   ```
   *Note: This generates `apps/backend/data/vendors_prod_dump.json.gz`.*

2. **Commit and Push the Dump:**
   The production restore script reads the dump file from the repository, so you must commit it:
   ```bash
   git add apps/backend/data/vendors_prod_dump.json.gz
   git commit -m "chore: update vendor dump with top 100 CPG brands"
   git push origin dev
   ```

3. **Trigger the Production Restore:**
   Wait for the Railway backend service to finish deploying the new commit. Once it is live, trigger the internal admin endpoint to restore the vendors into the production database:
   ```bash
   curl -X POST https://backend-production-96ef.up.railway.app/admin/ops/restore-vendors \
        -H "Authorization: Bearer 000000"
   ```
   *(Assuming `000000` is your `DEV_BYPASS_CODE` or equivalent admin token. Adjust URL to match your current Railway environment if needed).*
