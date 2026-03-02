# PRD-04: Fix JSON-in-String Data Model

## Business Outcome
- **Measurable impact:** Eliminate the JSON-in-string anti-pattern across core model fields while preserving runtime compatibility during migration.
- **Success criteria:** Core JSON-string fields converted to structured JSON columns (JSON/JSONB depending backend), write-side validation added, and read-path parsing simplified without breaking existing frontend assumptions; all tests pass.
- **Target users:** Developers (type-safe data access, queryable fields); indirectly users (fewer silent data corruption bugs).

## Scope
- **In-scope:**
  - Convert core JSON-string fields to structured JSON columns (JSON/JSONB) with Pydantic validators
  - Inline `RequestSpec` into `Row` (1:1 relationship, adds unnecessary JOIN)
  - Add Pydantic model validators for JSON fields that ensure valid JSON on write
  - Clean up `json.loads()` try/catch patterns in routes that read these fields
  - Alembic migration for column type changes
- **Out-of-scope:**
  - Normalizing JSON data into separate relational tables (e.g., chat_history → ChatMessage table) — deferred, too much risk
  - Intentional breaking API response changes (transitional dual-format compatibility is allowed)
  - Modifying fields on models being deleted in PRD-03 (Merchant, VendorProfile)

## Current State (Evidence)

### JSON-in-String Fields by Model

**Row model (`models/rows.py`):**

| Field | Type | Content | Read Sites |
|-------|------|---------|------------|
| `choice_factors` | `Optional[str]` | JSON array of factor objects | `store.ts:parseChoiceFactors()`, `ChoiceFactorPanel.tsx` |
| `choice_answers` | `Optional[str]` | JSON object of user answers | `store.ts:parseChoiceAnswers()`, `RequestTile.tsx` |
| `search_intent` | `Optional[str]` | JSON search intent structure | `routes/rows_search.py` |
| `provider_query_map` | `Optional[str]` | JSON mapping of provider→query | `routes/rows_search.py` |
| `chat_history` | `Optional[str]` | JSON array of chat messages | `routes/chat.py` |

**Bid model (`models/bids.py`):**

| Field | Type | Content | Read Sites |
|-------|------|---------|------------|
| `provenance` | `Optional[str]` | JSON provenance data | `BidWithProvenance` response model parses it on every read |
| `source_payload` | `Optional[str]` | JSON raw source data | Rarely accessed |

**RequestSpec model (`models/rows.py`):**

| Field | Type | Content | Read Sites |
|-------|------|---------|------------|
| `constraints` | `Optional[str]` | JSON constraints object | `routes/rows_search.py` |
| `preferences` | `Optional[str]` | JSON preferences object | Rarely accessed |

**VendorProfile model (being merged in PRD-03):**

| Field | Type | Content |
|-------|------|---------|
| `service_areas` | `Optional[str]` | JSON array of areas |
| `categories` | `Optional[str]` | JSON array of categories |

**Other models:**

| Model | Field | Content |
|-------|-------|---------|
| `SellerQuote` | `answers` | JSON answers to RFP questions |
| `SellerQuote` | `attachments` | JSON array of attachment URLs |
| `BugReport` | `diagnostics` | JSON diagnostic data |
| `BugReport` | `details` | JSON additional details |
| `Contract` | various | Being deleted in PRD-01 |

### The `RequestSpec` Table — Candidate for Inlining

`RequestSpec` is always 1:1 with `Row`:
- `Row.request_spec` relationship (one-to-one)
- Fields: `id`, `row_id` (FK), `item_name`, `constraints`, `preferences`, `created_at`
- `item_name` duplicates `Row.title`
- `constraints` and `preferences` are the only unique fields
- Every query that needs constraints does a JOIN or separate query

**Proposal:** Move `constraints` and `preferences` onto `Row` directly. Delete `RequestSpec` table.

### Current Parse Pattern (repeated everywhere)

```python
# Typical read pattern (routes/rows_search.py, routes/chat.py, etc.)
try:
    data = json.loads(row.choice_factors) if row.choice_factors else []
except (json.JSONDecodeError, TypeError):
    data = []
```

```typescript
// Frontend (store.ts)
export function parseChoiceFactors(raw: string | null): ChoiceFactor[] {
  if (!raw) return [];
  try { return JSON.parse(raw); } catch { return []; }
}
```

## Target State

### Priority 1: Core Row Fields (High Impact)

Convert these to structured JSON columns with Pydantic validators (Postgres JSONB where applicable; SQLModel `sa.JSON` for portability):

```python
class Row(SQLModel, table=True):
    # ... existing fields ...
    
    # Converted from Optional[str] to proper JSON columns
    choice_factors: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    choice_answers: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    search_intent: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    provider_query_map: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    chat_history: Optional[list] = Field(default=None, sa_column=Column(JSON))
    
    # Inlined from RequestSpec
    constraints: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    preferences: Optional[dict] = Field(default=None, sa_column=Column(JSON))
```

### Priority 2: Bid Fields (Medium Impact)

```python
class Bid(SQLModel, table=True):
    # ... existing fields ...
    provenance: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    source_payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))
```

### Priority 3: Other Fields (Lower Impact)

- `SellerQuote.answers` → JSON column
- `SellerQuote.attachments` → JSON column
- `BugReport.diagnostics` → JSON column
- `BugReport.details` → JSON column
- `Vendor.service_areas` → JSON column (after PRD-03)

### Write-Side Validation

Add Pydantic validators to ensure JSON fields receive valid structured data:

```python
from pydantic import field_validator

class Row(SQLModel, table=True):
    @field_validator('choice_factors', mode='before')
    @classmethod
    def validate_choice_factors(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return json.loads(v)  # Parse string → dict/list
        return v  # Already structured
```

This handles the transition period where some callers pass strings and others pass dicts.

### Read-Side Cleanup

After conversion and caller migration, remove `json.loads()` try/catch blocks in backend routes. Do this in phases to avoid mixed-type breakage during rollout.

```python
# BEFORE
try:
    factors = json.loads(row.choice_factors) if row.choice_factors else []
except: factors = []

# AFTER
factors = row.choice_factors or []
```

### Frontend Impact (second-pass correction)

Frontend currently parses `choice_factors`/`choice_answers` as strings in `store.ts`. During transition, backend should either:
- continue returning string-compatible payloads temporarily, or
- update frontend parsers to accept both string and object payloads before backend switch.

Do not assume immediate pass-through behavior until both sides are migrated.

## Migration Strategy

### Phase A: Add new JSON columns alongside old string columns

```sql
ALTER TABLE row ADD COLUMN choice_factors_json JSONB;
ALTER TABLE row ADD COLUMN choice_answers_json JSONB;
-- ... etc
```

### Phase B: Migrate data

```sql
UPDATE row SET choice_factors_json = choice_factors::jsonb 
WHERE choice_factors IS NOT NULL AND choice_factors != '';
```

### Phase C: Swap columns

```sql
ALTER TABLE row DROP COLUMN choice_factors;
ALTER TABLE row RENAME COLUMN choice_factors_json TO choice_factors;
```

### Phase D: Inline RequestSpec (defer-friendly)

```sql
ALTER TABLE row ADD COLUMN constraints JSONB;
ALTER TABLE row ADD COLUMN preferences JSONB;

UPDATE row SET constraints = rs.constraints::jsonb, preferences = rs.preferences::jsonb
FROM request_spec rs WHERE rs.row_id = row.id;

DROP TABLE request_spec;
```

**Recommended second-pass sequencing:** do phases A-C first, ship and verify, then perform RequestSpec inlining in a dedicated follow-up migration.

## User Flow
No intended user flow change. However, API payload field types may transition from stringified JSON to structured objects. Treat this as a compatibility migration and validate frontend parsing paths explicitly.

## Business Requirements

### Authentication & Authorization
- No auth changes

### Monitoring & Visibility
- After migration: verify row counts, sample data integrity
- Monitor for `json.JSONDecodeError` in logs (should drop to zero)

### Performance Expectations
- JSONB columns are slightly faster to read (no application-level parsing)
- JSONB columns support indexing for future query needs
- RequestSpec inline eliminates one JOIN per row query

### Data Requirements
- **Critical:** All existing JSON string data must parse successfully during migration
- **Risk:** Malformed JSON strings will fail cast — must handle with guarded conversion and pre-scan
- Migration must be reversible (downgrade re-adds string columns)
- Use phased dual-read/dual-write or compatibility validators to handle mixed historical records

### UX & Accessibility
- No UI changes

### Privacy, Security & Compliance
- No change in data access patterns

## Dependencies
- **Upstream:** PRD-03 (Vendor Model) — vendor fields should be settled before converting vendor JSON fields
- **Downstream:** PRD-05 (Frontend State) — simplified data flow benefits from cleaner backend data shapes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Malformed JSON in existing data fails migration | High | Pre-scan: `SELECT id FROM row WHERE choice_factors IS NOT NULL AND choice_factors NOT LIKE '{%' AND choice_factors NOT LIKE '[%'` |
| Railway Postgres version doesn't support JSONB | High | Railway uses Postgres 17 — JSONB supported since Postgres 9.4. Not a risk. |
| Frontend breaks because API returns object instead of string | High | Add Pydantic `field_validator` that accepts both string and dict during transition; frontend `parseChoiceFactors` already handles both |
| RequestSpec inline loses data | Medium | Verify 1:1 cardinality before migration: `SELECT row_id, COUNT(*) FROM request_spec GROUP BY row_id HAVING COUNT(*) > 1` |
| Performance regression from JSONB columns | Low | JSONB is faster than application-level JSON.parse; no indexing needed yet |

## Acceptance Criteria (Business Validation)
- [ ] `Row.choice_factors`, `Row.choice_answers`, `Row.search_intent`, `Row.provider_query_map`, `Row.chat_history` are structured JSON columns
- [ ] Frontend parsers are verified compatible with migrated payload types before removing backend string fallbacks
- [ ] `Row.constraints`, `Row.preferences` inlined from `RequestSpec` (if Phase D executed)
- [ ] `request_spec` table dropped only after dedicated migration verification
- [ ] `Bid.provenance`, `Bid.source_payload` are structured JSON columns
- [ ] Zero `json.loads()` calls for converted fields in route handlers
- [ ] Pydantic validators accept both string and dict input (transition safety)
- [ ] Frontend `parseChoiceFactors()` / `parseChoiceAnswers()` still work (graceful degradation)
- [ ] All existing data migrated successfully (row count preserved)
- [ ] All tests pass
- [ ] Manual smoke test: create row via chat → choice factors render → answers display correctly

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 6: JSON-in-String Anti-Pattern

---
**Note:** Technical implementation decisions are made during /plan and /task.
