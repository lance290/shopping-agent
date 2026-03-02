# PRD: VendorProfile Directory Cutover

## Status: In Progress
## Priority: P0
## Phase: Marketplace Pivot

---

## Business Outcome
Migrate the vendor directory from an in-memory Python dict (`VENDORS` in `services/vendors.py`) to a persistent `vendor_profile` database table with pgvector embedding support. This enables:
- **Infinite category support** — new vendor categories added via seed/crawl without code changes
- **Semantic vendor retrieval** — pgvector embeddings for hybrid lexical+vector search
- **Location bias scoring** — future proximity-based vendor ranking
- **Merchant onboarding link** — directory vendors can optionally link to an onboarded `Merchant`

**North Star alignment**: Seller response rate >20%, intent-to-close >5% — both require a scalable vendor directory beyond hardcoded lists.

---

## Scope

### In Scope
1. `VendorProfile` SQLModel + Alembic migration (vector extension + table)
2. Seed script writes to `vendor_profile` (not `Seller`)
3. Outreach routes (`GET /vendors/{category}`, `POST /rows/{row_id}/vendors`, `POST /rows/{row_id}/trigger`) read from `VendorProfile`
4. `Bid.seller_id` stays `NULL` for directory vendors; contact info on Bid directly
5. pgvector dependency added to `pyproject.toml` + `requirements.txt`
6. Migration runs automatically on deploy via `start.sh`

### Out of Scope
- Embedding generation (TODO #20 — pgvector semantic retrieval)
- Full cutover of `vendor_discovery.py` and `sourcing/repository.py` (still use in-memory for WattData mock)
- Removing the in-memory `VENDORS` dict entirely (still used by search and sourcing)
- Merchant self-registration changes
- Frontend category-agnostic card refactor

---

## User Flow
1. **Seed**: `python scripts/seed_vendors.py` upserts `VendorProfile` records from `VENDORS` dict
2. **Browse**: `GET /outreach/vendors/{category}` returns tiles from `vendor_profile` table
3. **Persist**: `POST /outreach/rows/{row_id}/vendors` creates `Bid` records with `seller_id=NULL`
4. **Outreach**: `POST /outreach/rows/{row_id}/trigger` sends RFP emails to vendors from `vendor_profile`

---

## Cross-Cutting Concerns

### Data Requirements
- PostgreSQL with `vector` extension enabled
- `vendor_profile` table with indexes on `category`, `company`, `contact_email`, `merchant_id`
- Embedding column: `vector(1536)` nullable

### Performance
- Category lookup is indexed — O(log n)
- No N+1 queries in vendor tile endpoints

### Security
- No PII exposure beyond what's already in outreach emails
- pgvector extension must be enabled by superuser or `rds_superuser`

### Monitoring
- Seed script logs created/updated/error counts
- Deploy script runs `alembic upgrade heads` before server start

---

## Acceptance Criteria
1. `alembic upgrade heads` creates `vendor_profile` table with all columns and indexes
2. `seed_vendors.py` populates `vendor_profile` from in-memory registry (idempotent)
3. `GET /outreach/vendors/private_aviation` returns vendors from DB (not in-memory)
4. `POST /outreach/rows/{id}/vendors` creates Bids with `seller_id=NULL`
5. `POST /outreach/rows/{id}/trigger` sends emails using `VendorProfile` contacts
6. No `Seller` records created during seed or outreach flows
7. All other callsites (`search_vendors_endpoint`, `vendor_discovery`, `sourcing/repository`) continue to work (may still use in-memory until full cutover)

---

## Dependencies
- **Upstream**: pgvector extension available on PostgreSQL instance
- **Downstream**: TODO #20 (semantic retrieval) depends on this table existing
