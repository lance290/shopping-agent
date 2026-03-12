# PRD + Tech Spec: Search Infrastructure Root Causes

**Status:** Active — Blocking live search for geo-sensitive and vendor-directory queries
**Priority:** P0
**Date:** 2026-03-12
**Author:** Engineering
**Relates to:** PRD-Trusted-Search-Vendor-Network-Refactor

---

## 1. Problem Statement

Two independent infrastructure defects are preventing the search stack from returning results for geo-sensitive queries (e.g., "luxury realtors in Nashville TN") and vendor-directory queries (e.g., "investment grade Birkin bag"). These are not ranking or relevance bugs — the system is crashing before ranking can run.

### Observed Symptoms

| Symptom | Actual Cause |
|---------|-------------|
| Nashville real estate search returns zero agents | Geocoding silently fails; location resolution stored as "unresolved" |
| Chat says "searching Nashville" but results panel is empty | LLM understands the query; geocoding + vendor search crash underneath |
| Birkin bag search shows "bids_arriving" forever | Vendor lookup and bid persistence crash on missing DB columns |
| Row reload sometimes 404s for guest users | Row ownership check uses wrong identity column depending on endpoint |

### What This Is Not

- Not an LLM understanding problem (Nashville reaches `search_intent.raw_input` correctly)
- Not a ranking/filtering problem (search crashes before scoring runs)
- Not a frontend rendering problem (backend returns empty or errors)

---

## 2. Root Cause 1: Split-Brain Geocoding Contract

### Summary

The app has **two geocoding services** that produce **incompatible LocationResolution objects**. The canonical model uses `lat`/`lon`; the older geocoder writes `latitude`/`longitude`. The chat flow calls the old geocoder, then tries to read fields that don't exist on the model, causing a silent `AttributeError` that gets caught and stored as `status: "unresolved"`.

### Canonical Model (source of truth)

**File:** `apps/backend/sourcing/models.py` lines 42-49

```python
class LocationResolution(BaseModel):
    normalized_label: Optional[str] = None
    lat: Optional[float] = None          # <-- canonical
    lon: Optional[float] = None          # <-- canonical
    precision: Optional[LocationPrecision] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    status: LocationResolutionStatus = "unresolved"
```

### Old Geocoder (writes wrong fields)

**File:** `apps/backend/services/geocoding.py`

`GeocodingService.resolve_location()` constructs `LocationResolution` with fields that **do not exist** on the model:

| Field written by old geocoder | Exists on LocationResolution? |
|-------------------------------|-------------------------------|
| `latitude` | NO — model has `lat` |
| `longitude` | NO — model has `lon` |
| `query` | NO |
| `display_name` | NO — model has `normalized_label` |
| `confidence` | NO |
| `raw_response` | NO |
| `error` | NO |

Because Pydantic v2 silently ignores extra fields by default, the object is created successfully but `lat` and `lon` are **always None**, even after a successful geocode.

### Consumer That Crashes

**File:** `apps/backend/routes/chat_helpers.py` line 126

```python
f"status={resolution.status}, lat={resolution.latitude}, lon={resolution.longitude}"
```

This reads `.latitude` / `.longitude` which do not exist on the model → `AttributeError` → caught by the surrounding `except` → stored as `"unresolved"`.

### New Geocoder (correct, but only used in one path)

**File:** `apps/backend/services/location_resolution.py`

`LocationResolutionService.resolve()` correctly writes `lat` and `lon`. This service is used by `SourcingService._resolve_search_locations()` during the search execution phase, but **not** during the initial chat/row-creation geocoding in `chat_helpers.py`.

### Impact

- **Every location geocoded during chat/row creation** gets silently downgraded to `unresolved`
- The vendor GEO CTE in `vendor_provider.py` receives `geo_lat = None`, `geo_lon = None`
- Geo proximity scoring is skipped entirely
- Text-only fallback matching ("Nashville" in `store_geo_location`) is the only remaining signal, and it's weak

### Failure Chain

```
User types "luxury realtors in Nashville TN"
  → LLM extracts location_context.targets.service_location = "Nashville, TN"
  → chat_helpers._resolve_all_location_targets() calls GeocodingService
  → GeocodingService.resolve_location("Nashville, TN") calls Nominatim
  → Nominatim returns lat=36.16, lon=-86.78 ✓
  → GeocodingService constructs LocationResolution(latitude=36.16, longitude=-86.78)
  → Pydantic silently drops latitude/longitude (not in schema), lat/lon stay None
  → chat_helpers logs resolution.latitude → AttributeError
  → except catches it → stores {"status": "unresolved"}
  → Row.search_intent.location_resolution.service_location = unresolved
  → Vendor search receives geo_lat=None, geo_lon=None
  → GEO CTE returns zero rows
  → No Nashville agents
```

**Critical detail:** This is a double-bug. Even if the `AttributeError` on the log line (Step 8) were fixed, the result would still be broken: `model_dump()` at line 123 would store `{"lat": None, "lon": None, "status": "resolved"}` — a "resolved" location with **no coordinates**. The vendor search would still receive `geo_lat=None, geo_lon=None` and skip all geo matching. The field-name mismatch in `GeocodingService` is the primary root cause; the log-line crash is secondary.

---

## 3. Root Cause 2: Vendor ORM / DB Schema Drift

### Summary

The `Vendor` ORM model (`models/bids.py`) defines columns that **do not exist** in the live `vendor` database table. Any code path that loads a full `Vendor` object or selects these columns in raw SQL crashes with `ProgrammingError` or `UndefinedColumnError`.

### Exact Drift

**ORM fields that DO NOT exist in the live DB:**

| ORM Field | Type | Impact |
|-----------|------|--------|
| `contact_title` | `Optional[str]` | Crashes eager load of `Bid.seller` |
| `contact_form_url` | `Optional[str]` | Crashes full Vendor load |
| `booking_url` | `Optional[str]` | Crashes full Vendor load |
| `vendor_type` | `Optional[str]` | Crashes full Vendor load |
| `secondary_categories` | `JSON` | Crashes full Vendor load |
| `service_regions` | `JSON` | Crashes full Vendor load |
| `source_provenance` | `Optional[str]` | Crashes full Vendor load |
| `trust_score` | `Optional[float]` | Crashes vendor search SQL + full load |
| `last_verified_at` | `Optional[datetime]` | Crashes full Vendor load |
| `last_contact_validated_at` | `Optional[datetime]` | Crashes full Vendor load |

**Live DB columns (37 total, confirmed via `information_schema`):**

```
id, name, email, domain, phone, website, category, specialties,
description, tagline, image_url, profile_text, embedding,
embedding_model, embedded_at, contact_name, is_verified, status,
user_id, stripe_account_id, stripe_onboarding_complete,
default_commission_rate, verification_level, reputation_score,
created_at, updated_at, _migrated_from, tier_affinity,
price_range_min, price_range_max, slug, seo_content, schema_markup,
store_geo_location, search_vector, latitude, longitude
```

**Reverse drift (DB columns NOT in ORM, non-crash but worth noting):**

| DB Column | Notes |
|-----------|-------|
| `_migrated_from` | Legacy migration marker; unused by app code |
| `search_vector` | Used in raw SQL but not via ORM; harmless |

### Affected Code Paths

| Code Path | How It Breaks |
|-----------|---------------|
| `GET /rows` — eager load `Bid.seller` | `ProgrammingError: column vendor_1.contact_title does not exist` |
| `GET /rows/{id}` — eager load `Bid.seller` | Same as above |
| `SourcingService._get_or_create_seller()` | Full `Vendor` load crashes on missing columns |
| `vendor_provider.py` hybrid SQL | Selects `trust_score` directly → `UndefinedColumnError` |
| Any admin/bookmark path loading full Vendor | Same class of crash |

### Current Bandaids (applied in previous session, not permanent fixes)

- `rows.py`: `load_only(Vendor.id, Vendor.name, Vendor.domain)` on eager loads
- `service.py`: `load_only(Seller.id, Seller.name, Seller.domain)` in `_get_or_create_seller`
- `vendor_provider.py`: `0::float AS trust_score` hardcoded in SQL

These prevent crashes but are fragile — any new code path that touches `Vendor` without the same guards will crash.

---

## 4. Secondary Issue: Inconsistent Guest Row Ownership

### Summary

Guest (anonymous) users are identified by `anonymous_session_id` on the `Row` model, but many endpoints still look up rows by `Row.user_id == guest_user_id`. Since there is only one shared guest user record (`id=2, email=guest@buy-anything.com`), all guest rows share the same `user_id`, making row isolation dependent on `anonymous_session_id`. Endpoints that don't check it return wrong rows or 404.

### Affected Endpoints

| Endpoint | Uses `anonymous_session_id`? |
|----------|------------------------------|
| `GET /rows` | YES (fixed) |
| `GET /rows/{id}` | YES (fixed) |
| `PATCH /rows/{id}` | YES (fixed) |
| `POST /rows/{id}/search` | NO — still uses `user_id` |
| `POST /rows/{id}/search/stream` | NO — still uses `user_id` |
| `POST /api/search` (enriched) | YES (fixed) |
| `DELETE /rows/{id}` | NO |
| `POST /rows/{id}/duplicate` | YES (fixed) |
| `POST /rows/{id}/outcome` | NO |
| `POST /rows/{id}/feedback` | NO |
| Chat endpoint row lookups | NO — uses `user_id` |

---

## 5. Fix Plan

### Phase 1: Unify Geocoding Contract (P0, ~2 hours)

**Goal:** One geocoding service, one data shape, one code path.

#### Step 1.1: Delete the old geocoder or align its output

**Option A (preferred):** Replace all `GeocodingService` usage with `LocationResolutionService`.

- `chat_helpers._resolve_all_location_targets()` currently imports `GeocodingService`
- Change it to use `LocationResolutionService` instead
- This requires passing a DB session (for cache), which `_resolve_all_location_targets` doesn't currently have
- Thread the session through from the chat endpoint

**Option B (faster):** Fix `GeocodingService` to write `lat`/`lon` instead of `latitude`/`longitude`.

- Change all `LocationResolution(latitude=..., longitude=...)` calls to `LocationResolution(lat=..., lon=...)`
- Remove non-existent fields: `query`, `display_name`, `confidence`, `raw_response`, `error`
- Map to canonical fields: `query` → `normalized_label`, `display_name` → `normalized_label`

#### Step 1.2: Fix the log line in chat_helpers.py

```python
# FROM:
f"status={resolution.status}, lat={resolution.latitude}, lon={resolution.longitude}"
# TO:
f"status={resolution.status}, lat={resolution.lat}, lon={resolution.lon}"
```

#### Step 1.3: Flush the geocode cache for Nashville

Any previously cached "unresolved" Nashville entries in `location_geocode_cache` should be expired or deleted so the corrected geocoder can re-resolve them.

```sql
DELETE FROM location_geocode_cache WHERE normalized_query LIKE '%nashville%';
```

#### Step 1.4: Regression test

- Test: geocode "Nashville, TN" → `status="resolved"`, `lat≈36.16`, `lon≈-86.78`
- Test: full chat flow with "luxury realtors in Nashville TN" → `location_resolution.service_location.status == "resolved"`
- Test: vendor GEO CTE receives non-null `geo_lat`, `geo_lon`

### Phase 2: Align Vendor Schema (P0, ~1 hour)

**Goal:** The live DB and the ORM agree on every column.

#### Step 2.1: Run an Alembic migration to add the missing columns

```sql
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS contact_title TEXT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS contact_form_url TEXT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS booking_url TEXT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS vendor_type TEXT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS secondary_categories JSONB;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS service_regions JSONB;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS source_provenance TEXT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS trust_score FLOAT;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP;
ALTER TABLE vendor ADD COLUMN IF NOT EXISTS last_contact_validated_at TIMESTAMP;
```

#### Step 2.2: Remove all `load_only` bandaids

Once the schema matches, revert:
- `rows.py` eager-load restrictions
- `service.py` `_get_or_create_seller` `load_only`
- `vendor_provider.py` `0::float AS trust_score` hack

#### Step 2.3: Regression test

- Test: `GET /rows` with bids → no `ProgrammingError`
- Test: `_get_or_create_seller("Test Vendor", "test.com")` → creates/loads without error
- Test: vendor directory hybrid SQL executes without `UndefinedColumnError`

### Phase 3: Unify Row Access (P1, ~1 hour)

**Goal:** One shared function resolves row ownership for all endpoints.

#### Step 3.1: Create `resolve_accessible_row()`

```python
async def resolve_accessible_row(
    session: AsyncSession,
    row_id: int,
    user_id: int,
    is_guest: bool,
    anonymous_session_id: Optional[str],
) -> Row:
    """Single source of truth for row ownership resolution."""
    clauses = [Row.id == row_id]
    if is_guest:
        if not anonymous_session_id:
            raise HTTPException(status_code=404, detail="Row not found")
        clauses.append(Row.anonymous_session_id == anonymous_session_id)
    else:
        clauses.append(Row.user_id == user_id)
    result = await session.exec(select(Row).where(*clauses))
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row
```

#### Step 3.2: Replace all inline row lookups

Wire every row-touching endpoint through `resolve_accessible_row()`:
- `rows.py`: read, update, delete, duplicate, outcome, feedback
- `rows_search.py`: search, search/stream
- `search_enriched.py`: enriched search
- `chat.py`: all row lookups inside SSE generator

#### Step 3.3: Regression test

- Test: guest user can search, reload, and update the same row
- Test: guest user cannot access another guest's row
- Test: authenticated user row access unchanged

---

## 6. Roadmap

```
Phase 1: Unify Geocoding         ████████░░  P0  ~2 hrs
Phase 2: Align Vendor Schema     ████████░░  P0  ~1 hr
Phase 3: Unify Row Access        ██████░░░░  P1  ~1 hr
──────────────────────────────────────────────────────
Live verification                ████░░░░░░  P0  ~30 min
  - Nashville real estate agents appear with geo scores
  - Birkin bag search persists bids
  - Guest session row lifecycle works end-to-end
```

### Phase 1 and 2 are blocking. Phase 3 is important but can follow.

---

## 7. Success Criteria

| Criterion | How to verify |
|-----------|---------------|
| "luxury realtors in Nashville TN" returns Nashville-area agents | `location_resolution.service_location.status == "resolved"` AND vendor results have `geo_distance_miles < 75` |
| "investment grade Birkin bag" persists bids | `GET /rows/{id}` returns row with `bids.length > 0` |
| No `ProgrammingError` or `UndefinedColumnError` in backend logs | Grep backend logs after full search cycle |
| Guest user can complete full search lifecycle | Create row → search → reload → update → search again, all via anonymous session |
| Geocode cache stores resolved Nashville entry | `SELECT * FROM location_geocode_cache WHERE normalized_query LIKE '%nashville%'` returns `status='resolved'` |

---

## 8. Non-Goals

- Vendor ranking/relevance tuning (separate concern; blocked by these infrastructure failures)
- LLM vetting/reranking improvements (can't be tested until search actually returns results)
- UI changes to show geocode status (desirable but not blocking)
- Rate limiting for anonymous searches (deferred)
- Gemini embedding fallback for vendor directory (separate concern)

---

## 9. Files Reference

| File | Role | Issue |
|------|------|-------|
| `apps/backend/sourcing/models.py` | Canonical `LocationResolution` model | Source of truth: `lat`, `lon` |
| `apps/backend/services/geocoding.py` | Old geocoder | Writes `latitude`, `longitude` (wrong) |
| `apps/backend/services/location_resolution.py` | New geocoder | Writes `lat`, `lon` (correct) |
| `apps/backend/routes/chat_helpers.py` | Chat → row creation geocoding | Reads `resolution.latitude` (crashes) |
| `apps/backend/models/bids.py` | `Vendor` ORM model | 10 fields not in live DB |
| `apps/backend/sourcing/vendor_provider.py` | Vendor directory SQL | References `trust_score` (missing) |
| `apps/backend/sourcing/service.py` | Bid persistence | `_get_or_create_seller` full-loads `Vendor` |
| `apps/backend/routes/rows.py` | Row CRUD | Partially fixed for guest access |
| `apps/backend/routes/rows_search.py` | Row search | NOT fixed for guest access |
| `apps/backend/routes/search_enriched.py` | Enriched search | Fixed for guest access |
| `apps/backend/routes/chat.py` | Chat SSE | Uses `user_id` for row lookups (not session) |
