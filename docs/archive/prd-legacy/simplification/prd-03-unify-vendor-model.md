# PRD-03: Unify the Vendor Model

## Business Outcome
- **Measurable impact:** Merge 3 overlapping vendor/seller entities (`Seller`, `VendorProfile`, `Merchant`) into a single `Vendor` model. Eliminates field duplication (email appears in 3 tables), FK confusion (bids reference `Seller` but search uses `VendorProfile`), and the existence of a `Merchant` table with zero real registrations.
- **Success criteria:** Single `vendor` table with all necessary fields; `Bid.vendor_id` FK replaces `Bid.seller_id`; `VendorProfile` embeddings preserved in `Vendor`; 162 seeded vendor profiles migrated; `Merchant` table dropped; all routes updated; all tests pass.
- **Target users:** Developers (one entity to reason about); indirectly users (fewer bugs from model confusion).

## Scope
- **In-scope:**
  - Create unified `Vendor` model combining fields from `Seller`, `VendorProfile`, `Merchant`
  - Write Alembic migration to:
    - Create `vendor` table
    - Migrate data from `seller`, `vendor_profile`, `merchant` into `vendor`
    - Update `bid.seller_id` → `bid.vendor_id` FK
    - Drop `seller`, `vendor_profile`, `merchant` tables
  - Update all backend routes, services, and models that reference `Seller`, `VendorProfile`, or `Merchant`
  - Update frontend types and components that reference `Seller` or vendor data
  - Delete `models/marketplace.py` (VendorProfile, Merchant definitions)
  - Move remaining marketplace models (SellerQuote, OutreachEvent, DealHandoff) to `models/deals.py` or keep in place
- **Out-of-scope:**
  - Changing vendor search logic (embedding-based search stays as-is)
  - Building new vendor management UI
  - Stripe Connect integration (nullable field preserved for future)

## Current State (Evidence)

### Three Overlapping Models

| Field | `Seller` (bids.py) | `VendorProfile` (marketplace.py) | `Merchant` (marketplace.py) |
|-------|--------------------|---------------------------------|----------------------------|
| **Table** | `seller` | `vendor_profile` | `merchant` |
| **name** | `name: str` | `business_name: str` | `business_name: str` |
| **email** | `email: Optional[str]` | `contact_email: Optional[str]` | `email: str` |
| **phone** | `phone: Optional[str]` | `contact_phone: Optional[str]` | `phone: Optional[str]` |
| **website/domain** | `domain: Optional[str]` | `website: Optional[str]` | `website: Optional[str]` |
| **category** | `category: Optional[str]` | `category: Optional[str]` | `categories: Optional[str]` (JSON) |
| **service_areas** | ❌ | `service_areas: Optional[str]` (JSON) | ❌ |
| **embedding** | ❌ | `embedding` (Vector/JSON) | ❌ |
| **status** | ❌ | ❌ | `status: str` (pending/verified/suspended) |
| **stripe** | ❌ | ❌ | `stripe_account_id`, `stripe_onboarding_complete` |
| **reputation** | ❌ | ❌ | `reputation_score`, `verification_level` |
| **Used by** | `Bid.seller_id` FK; active | Vector search; seeded directory data | Registration route; active flow |

### FK Relationships (second-pass corrected)

- `Bid.seller_id` → `seller.id` (active, used by bid creation)
- `Merchant.seller_id` → `seller.id` (optional link)
- `SellerQuote`, `OutreachEvent`, and `DealHandoff` currently store vendor identity via email/name fields (no `seller_id` FK)
- `VendorProfile.merchant_id` → `merchant.id` (optional link)

### Data Volumes (second-pass corrected)

- `seller` table: grows with bids (auto-created during sourcing)
- `vendor_profile` table: seeded directory records with embeddings
- `merchant` table: active registration flow exists (`/merchants/register`), so assume non-zero production data and migrate conservatively

## Target Model

```python
class Vendor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Identity
    name: str                                    # from Seller.name / VendorProfile.business_name
    domain: Optional[str] = None                 # from Seller.domain / VendorProfile.website
    email: Optional[str] = None                  # from Seller.email / VendorProfile.contact_email
    phone: Optional[str] = None                  # from Seller.phone / VendorProfile.contact_phone
    website: Optional[str] = None                # from VendorProfile.website
    
    # Classification
    category: Optional[str] = None               # from Seller.category / VendorProfile.category
    service_areas: Optional[str] = None          # JSON, from VendorProfile.service_areas
    
    # Search
    embedding: Optional[...] = None              # Vector(1536) or JSON, from VendorProfile.embedding
    description: Optional[str] = None            # from VendorProfile.description
    
    # Status & Trust
    status: str = "unverified"                   # unverified, verified, suspended
    
    # Future
    stripe_account_id: Optional[str] = None      # nullable, for future Connect
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    bids: List["Bid"] = Relationship(back_populates="vendor")
    quotes: List["SellerQuote"] = Relationship(back_populates="vendor")
```

## User Flow
No direct user flow change. Vendors display the same data in tiles. The backend returns the same shape of data. The only difference is the source table.

## Business Requirements

### Authentication & Authorization
- No auth changes — vendor data is public (displayed on bid tiles)

### Monitoring & Visibility
- After migration: verify `SELECT COUNT(*) FROM vendor` matches expected count
- Verify bid→vendor FK integrity: `SELECT COUNT(*) FROM bid WHERE vendor_id NOT IN (SELECT id FROM vendor)`

### Performance Expectations
- Vector search performance unchanged (same embedding data, same column type)
- Bid queries may be marginally faster (one JOIN instead of potential multi-table lookups)

### Data Requirements
- **Critical:** All 162 VendorProfile embeddings must be preserved in the migration
- **Critical:** All existing Seller records must be migrated (they're referenced by Bid FKs)
- **Do not assume drop-only for Merchant:** merchant registrations may exist and must be migrated
- Migration strategy:
  1. Create `vendor` table
  2. INSERT INTO vendor from `seller` (preserve IDs for FK integrity)
  3. Migrate `merchant` and `vendor_profile` attributes into `vendor` with deterministic merge keys (email/domain/company)
  4. UPDATE `bid` SET `vendor_id = seller_id` (since seller IDs are preserved)
  5. Rename `bid.seller_id` to `bid.vendor_id`
  6. Decide how to handle legacy `merchant.seller_id` link (rename or replace via mapping table) before dropping old tables
  7. DROP `seller`, `vendor_profile`, `merchant` only after reconciliation checks pass

### UX & Accessibility
- No UI changes in this effort (frontend types updated to match, but display unchanged)

### Privacy, Security & Compliance
- Vendor contact info (email, phone) moves tables but retains same access controls

## Migration Details

### ID Preservation Strategy

**Sellers:** Preserve their IDs in the `vendor` table so that `bid.seller_id` → `bid.vendor_id` works without updating every bid row's FK value.

**VendorProfiles:** Assign new IDs (offset from max seller ID) since no FK references them.

**Merchants:** Treat as potentially populated; migrate and reconcile before table drop.

### Column Rename on Dependent Tables (second-pass corrected)

| Table | Old Column | New Column | Notes |
|-------|-----------|------------|-------|
| `bid` | `seller_id` | `vendor_id` | Required FK migration |
| `merchant` | `seller_id` | TBD | Optional legacy link; migration design decision required |

### Backend Code Updates

| File | Change |
|------|--------|
| `models/bids.py` | Remove `Seller` class; update `Bid.seller_id` → `Bid.vendor_id`; update relationship |
| `models/marketplace.py` | Remove `VendorProfile`, `Merchant`; keep `SellerQuote`, `OutreachEvent`, `DealHandoff`; preserve email-based vendor references unless explicitly redesigned |
| `models/__init__.py` | Add `Vendor` to exports; remove `Seller`, `VendorProfile`, `Merchant` |
| `routes/seller.py` | Update all `Seller` references → `Vendor`; update queries |
| `routes/merchants.py` | Keep behavior via compatibility layer or migrate to unified `Vendor` route; do not drop registration flow |
| `routes/bids.py` | Update `Seller` references → `Vendor` |
| `routes/outreach.py` | Update any seller-model joins while preserving existing email-based outreach fields |
| `routes/quotes.py` | Update seller/model references as needed; no direct `seller_id` rename exists today |
| `services/vendors.py` | Update `VendorProfile` → `Vendor` |
| `sourcing/repository.py` | Update any `Seller` creation → `Vendor` creation |
| Frontend types | Update `Seller` → `Vendor` in TypeScript interfaces |

## Dependencies
- **Upstream:** PRD-01 (Dead Backend) should be done first so we don't waste time updating routes that will be deleted
- **Downstream:** PRD-04 (Fix Data Model) builds on the cleaner model structure

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration loses vendor embeddings | Critical | Verify row count and sample embeddings before and after migration |
| FK integrity breaks on bid→vendor | Critical | Preserve seller IDs in vendor table; verify with COUNT query |
| Column rename breaks a query we missed | High | Full `grep -rn "seller_id"` across entire backend before migration |
| Railway migration fails | High | Test migration on local DB copy first; ensure downgrade works |
| Frontend displays break | Medium | Search for all `seller` references in `.tsx`/`.ts` files |

## Acceptance Criteria (Business Validation)
- [ ] Single `vendor` table exists with all fields from target model
- [ ] `seller`, `vendor_profile`, `merchant` tables dropped
- [ ] All 162 vendor embeddings preserved (verified by count + sample check)
- [ ] `Bid.vendor_id` FK works (no orphaned references)
- [ ] Merchant registration data is preserved through migration (no data loss for existing onboarded records)
- [ ] `SellerQuote`, `OutreachEvent`, and `DealHandoff` continue to resolve vendor identity correctly after migration
- [ ] `grep -rn "Seller\b" apps/backend/models/` returns 0 results (class fully removed)
- [ ] `grep -rn "VendorProfile\b" apps/backend/` returns 0 results
- [ ] `grep -rn "Merchant\b" apps/backend/models/` returns 0 results (class fully removed)
- [ ] Backend starts cleanly
- [ ] All tests pass
- [ ] Vendor search (embedding-based) still returns results
- [ ] Bid tiles display vendor name correctly

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 3: Three Vendor Entities, Zero Clarity

---
**Note:** Technical implementation decisions are made during /plan and /task.
