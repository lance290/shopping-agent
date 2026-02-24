# PRD: UHNW Luxury Procurement — Phased Execution Plan

> Distilled from strategic research (tweak.md), grounded in the actual BuyAnything codebase.
> Each phase builds incrementally on existing infrastructure. No greenfield rewrites.

---

## Executive Summary

BuyAnything already has the skeleton for luxury procurement:
- **Chat-driven procurement** with LLM decision engine (`services/llm.py`)
- **Desire tier classification** (`commodity → advisory`) that routes high-value requests to vendor directory
- **3,000+ vendor directory** with pgvector embeddings for specialist matching
- **Deal pipeline** (Phase 1 shipped) with `DealHandoff` model tracking buyer-vendor introductions
- **Stripe Connect** onboarding for vendors (`routes/stripe_connect.py`)
- **Checkout** with `application_fee_amount` for platform commission (`routes/checkout.py`)

The gap: the system treats a "$15 gift card" and a "$15M jet charter" identically after classification. UHNW procurement needs **memory**, **curation** (not just search), **trust signals**, and **commission tracking at deal close** (not at checkout).

---

## Core Principle: "Buy ANYTHING" Means Everything Works

The name is "BuyAnything" — not "BuyLuxury." The commodity experience (Amazon, Google Shopping, eBay) must be just as polished and effortless as the bespoke vendor matching. This is the platform's moat: **one interface for everything from AA batteries to a Gulfstream.**

### Marketplace Parity Requirements

Every search provider must feel like a first-class citizen:

| Provider | Tier | Status | Revenue Model |
|----------|------|--------|---------------|
| **Amazon** | commodity / considered | Active, default ON | Affiliate (Amazon Associates) |
| **Google Shopping** (SerpAPI) | commodity / considered | Active, default ON | Affiliate (future) — accept cost for now |
| **eBay** | commodity / considered | Active, toggle available | Affiliate (eBay Partner Network) |
| **Bespoke** (Vendor Directory) | service / bespoke / high_value | Active, default ON | Commission on DealHandoff |

### What "Parity" Means Concretely

1. **Unified result cards.** An Amazon result and a Bespoke vendor result should both render in `OfferTile.tsx` with equal visual weight. No provider should feel like a second-class citizen.
2. **Consistent deal flow.** "Buy Now" (Amazon/eBay/Google → affiliate redirect) and "Select" (Bespoke → DealHandoff) are parallel paths, not one being a fallback for the other.
3. **Provider health monitoring.** If Amazon API is slow or SerpAPI is rate-limited, surface that in `rowProviderStatuses` so the user knows — don't silently fail.
4. **Cross-provider comparison.** The Decision Memo (Phase 2) should be able to compare an Amazon result against a Bespoke vendor quote. The LLM doesn't care where the result came from.
5. **Smart defaults.** All providers ON by default. The LLM's `desire_tier` classification handles routing — `commodity` queries naturally return more Amazon/Google results, `service` queries naturally return more Bespoke results. The user shouldn't have to think about toggles.

### Cost Reality

Google Shopping (SerpAPI) costs ~$0.01/search. At current volumes this is negligible. The strategic value of showing Google results — proving BuyAnything is a true "buy anything" platform — far outweighs the API cost. Revisit when volume exceeds 10K searches/month.

### Future Providers (Roadmap)

| Provider | When | Why |
|----------|------|-----|
| **Walmart** | Q2 2026 | Commodity coverage, affiliate program |
| **Etsy** | Q2 2026 | Handmade/bespoke bridge between commodity and vendor directory |
| **StockX** | Q3 2026 | Sneakers, luxury streetwear — authenticated marketplace |
| **1stDibs** | Q3 2026 | High-end furniture, art, jewelry |
| **Jettly / PrivateFly** | Q4 2026 | Direct aviation API (replaces vendor directory for jet charters) |

---

## What We're NOT Building (Yet)

These items from the research doc are deferred indefinitely:
- ADS-B flight tracking / maritime AIS integration
- GIA diamond certificate API verification
- Encrypted guest manifest vault with passport storage
- Off-market "invisible inventory" table
- Pinecone/Weaviate separate vector store (pgvector is sufficient)

---

## Phase 0: Foundation Tweaks (1-2 days) — READY NOW

**Goal:** Make the existing system behave better for high-value requests with zero new models.

### 0A. LLM Context Injection — User History Recall

**File:** `services/llm.py` → `make_unified_decision()`

The `ChatContext` model already accepts `conversation_history`, but it's scoped to the current session. For repeat users, the LLM has no memory of past requests.

**Change:** Before building the prompt in `make_unified_decision()`, query the user's last 5 completed rows (title + constraints + desire_tier) and inject them as a `BUYER HISTORY` block in the system prompt.

```
BUYER HISTORY (this user's past requests):
- "Private jet SAN→EWR, 7 pax, Feb 13" (service, completed)
- "Custom engagement ring, 2ct emerald cut" (bespoke, selected)
- "Catering for 200, Mediterranean cuisine" (service, completed)

Use this history to:
1. Infer unstated preferences (e.g., they charter jets often → likely want mid-size or better)
2. Avoid re-asking questions you can infer from history
3. Reference past requests when relevant ("Similar to your February charter...")
```

**Touched files:**
- `services/llm.py` — add history query + prompt block
- `routes/chat.py` — pass `user_id` into `ChatContext`
- `models/rows.py` — no changes (Row already has `user_id`, `title`, `desire_tier`, `structured_constraints`)

**Effort:** ~50 lines of code. No migrations.

### 0B. Curated Recommendations (Top 3 + Backups)

**File:** `sourcing/scorer.py`

For `desire_tier in (service, bespoke, high_value)`, change the result presentation logic:
- Instead of returning all results sorted by score, return **"Recommended" (top 1) + "Also Excellent" (2-3)** with explicit LLM-generated justification per result.
- Add a `recommendation_note` field to the bid response for high-tier requests.

**Touched files:**
- `sourcing/scorer.py` — tier-aware result capping
- `routes/rows_search.py` or `routes/chat.py` — pass recommendation notes to frontend
- `apps/frontend/app/components/OfferTile.tsx` — render `recommendation_note` when present

**Effort:** ~80 lines backend + ~20 lines frontend.

---

## Phase 1: Principal Preferences (1 week)

**Goal:** The "Memory Engine" — but built on what exists, not a new vector store.

### Data Model

The `UserPreference` table already exists in `models/admin.py`:

```python
class UserPreference(SQLModel, table=True):
    user_id: int
    preference_key: str   # "brand", "merchant", "price_range", "category"
    preference_value: str  # "Nike", "amazon.com", "50-200"
    weight: float = 1.0
```

**Extend with new preference_key types** (no schema change needed — it's already a free-form string):

| preference_key | preference_value (examples) | Source |
|---|---|---|
| `aircraft_preference` | `"mid-size, divan layout"` | Extracted from chat |
| `hotel_preference` | `"high-floor suites, Hôtel de Crillon"` | Extracted from chat |
| `dietary_restriction` | `"no shellfish, kosher available"` | Extracted from chat |
| `budget_range:aviation` | `"50000-150000"` | Inferred from past deals |
| `vendor_preference` | `"NetJets, Flexjet"` | Extracted from selections |
| `vendor_avoid` | `"XO, WheelsUp"` | Extracted from rejections |
| `general_note` | `"Always prefers direct flights"` | Extracted from chat |

### Preference Extraction Pipeline

**New function:** `services/preferences.py` → `extract_and_store_preferences()`

After every completed chat turn for authenticated users:
1. If `desire_tier in (service, bespoke, high_value)`, run a lightweight LLM call on the conversation to extract preferences.
2. Upsert into `UserPreference` (key + user_id is the uniqueness constraint).
3. Feed preferences back into the LLM prompt (Phase 0A's history block gets upgraded to include preferences).

**Touched files:**
- `services/preferences.py` (new, ~120 lines)
- `routes/chat.py` — call extraction after chat completion
- `services/llm.py` — inject preferences into prompt alongside history

### Preference Management UI

**New route:** `apps/frontend/app/account/preferences/page.tsx`

Simple settings page where users can view and edit their stored preferences. Table view with edit/delete. No complex UI — just a clean list.

**Effort:** ~200 lines backend + ~150 lines frontend.

---

## Phase 2: Decision Memos / Comparison Export (1 week)

**Goal:** The "one-click PDF" that EAs actually need. This is the killer feature for the EA persona.

### Backend: Memo Generation

**New endpoint:** `POST /api/rows/{row_id}/memo`

1. Fetch the row, its top 3 bids, choice factors, and choice answers.
2. Call LLM with a structured prompt to generate:
   - **Executive Summary** (why these 3 beat the others)
   - **Per-option breakdown** (price, key differentiators, match to stated preferences)
   - **Risk flags** (vendor unverified, no reviews, price outlier)
3. Return structured JSON that the frontend renders OR export as PDF.

**PDF Generation:** Use `weasyprint` (Python) or `@react-pdf/renderer` (frontend). Given the stack, frontend PDF generation from the memo JSON is simpler — no new backend dependency.

**Touched files:**
- `routes/rows.py` — new `/memo` endpoint (~80 lines)
- `services/llm.py` — new `generate_decision_memo()` function (~60 lines)
- `apps/frontend/app/components/DecisionMemo.tsx` (new, ~200 lines)
- `apps/frontend/app/components/RowStrip.tsx` — add "Generate Memo" button for `desire_tier != commodity`

### What the Memo Looks Like

```
┌─────────────────────────────────────────┐
│  DECISION MEMO                          │
│  Private Jet Charter: SAN → EWR         │
│  Prepared for: [Principal Name]         │
│  Date: Feb 23, 2026                     │
├─────────────────────────────────────────┤
│  EXECUTIVE SUMMARY                      │
│  3 options evaluated from 12 vendors.   │
│  Top pick: NetJets Citation XLS at      │
│  $45,000 — best match for your          │
│  preference for mid-size with divan.    │
├─────────────────────────────────────────┤
│  OPTION 1 (Recommended)                 │
│  NetJets — Citation XLS                 │
│  $45,000 | 4.5hr | 8 pax capacity      │
│  ✓ Divan layout (your preference)       │
│  ✓ YOM 2021, just completed 3-yr check  │
│  ⚠ No WiFi on this tail                 │
├─────────────────────────────────────────┤
│  OPTION 2                               │
│  Flexjet — Challenger 350               │
│  $62,000 | 4hr | 10 pax capacity       │
│  ✓ WiFi, full galley                    │
│  ✓ Larger cabin                         │
│  ⚠ $17k premium over Option 1           │
├─────────────────────────────────────────┤
│  [Export PDF]  [Share Link]  [Select]   │
└─────────────────────────────────────────┘
```

**Effort:** ~350 lines total across backend + frontend.

---

## Phase 3: Commission Tracking & Revenue (2 weeks)

**Goal:** Close the revenue loop. You already have Stripe Connect and checkout — now track commissions on high-value deals that close outside Stripe (via email/phone).

### The Problem

High-value deals ($10k+ jets, $50k+ yachts) don't go through a web checkout. They close via email introductions (your `DealHandoff`). You need to track:
1. That a deal was introduced (already done — `DealHandoff.status = "introduced"`)
2. That the vendor confirmed the deal closed (new)
3. What commission is owed (new)
4. That commission was paid (new)

### Data Model Extension

**Extend `DealHandoff`** (already has `deal_value`, `currency`, `status`):

```python
# New fields on DealHandoff
commission_rate: Optional[float] = None        # e.g., 0.05 for 5%
commission_amount: Optional[float] = None      # calculated or manual
commission_status: str = "pending"             # pending, invoiced, paid, waived
commission_paid_at: Optional[datetime] = None
vendor_confirmed_at: Optional[datetime] = None # vendor confirms deal closed
vendor_confirmed_value: Optional[float] = None # actual close price (may differ from quote)
```

### Commission Flow

1. **Deal introduced** → `DealHandoff` created with `commission_rate` from `Vendor.default_commission_rate` (already exists on vendor model)
2. **Vendor confirms close** → new endpoint `POST /api/deals/{handoff_id}/confirm` (vendor clicks link in email)
3. **Admin reviews** → admin dashboard shows pending commissions
4. **Invoice generated** → manual or Stripe Invoice API

### Vendor Confirmation Email

Extend `send_vendor_selected_email()` (already exists in `services/email.py`) to include a "Confirm Deal Closed" link that hits the confirmation endpoint.

### Admin Commission Dashboard

**New route:** `GET /api/admin/commissions`
- List all `DealHandoff` records with `status in (accepted, completed)` and their commission status
- Filter by date range, vendor, status
- Total pipeline value, total commissions earned/pending

**Frontend:** New tab in admin panel.

**Effort:** ~400 lines backend + ~250 lines frontend.

---

## Phase 4: Vendor Onboarding & Trust (2 weeks)

**Goal:** Make the vendor side of the marketplace trustworthy enough for high-value transactions.

> Note: Phase 6 PRDs (Customer Support & Trust Infrastructure) already exist in `docs/prd/phase6-customer-support/`. This phase cherry-picks the most critical items for UHNW.

### Priority Items (from Phase 6 audit)

1. **Fix B1:** `search_merchants()` filters `status=="verified"` but no merchant ever reaches that status → always returns 0 results. Add admin verification workflow.
2. **Fix B2:** `_get_merchant()` doesn't check status → suspended merchants can quote.
3. **Vendor tier badges** in OfferTile: "Verified", "Premium", "New" based on `Vendor.verification_level`.
4. **Commission agreement** as part of vendor onboarding — before a vendor receives buyer introductions, they must accept commission terms (stored on `Vendor`).

### Vendor Outreach Script (Automated)

The research doc's outreach script is good. Templatize it:

```
Subject: Verified Buyer Request — [Category] in [Location]

We represent a vetted buyer seeking [specific requirement].
We handle initial vetting and introductions.

Commission: [rate]% on confirmed close.
To receive buyer details, please confirm terms: [link]
```

This replaces the current generic outreach in `routes/outreach.py`.

**Effort:** ~300 lines backend + ~200 lines frontend.

---

## Phase 5: White-Label & COI Strategy (Future — No Code Yet)

This is a GTM/business phase, not a code phase. Capture the strategy but don't build:

- **White-label API**: Package the EA workspace + vendor directory as an API that wealth managers can embed. This is a packaging exercise on existing endpoints, not new code.
- **LinkedIn EA targeting**: Marketing playbook, not a feature.
- **"Procurement Audit" lead magnet**: Content marketing, not a feature.

**When to build:** After Phase 3 proves revenue, and after 10+ paying vendor relationships exist.

---

## Build Sequencing

| Phase | Duration | Dependencies | Revenue Impact |
|-------|----------|-------------|----------------|
| **0: Foundation Tweaks** | 1-2 days | None | Indirect (better UX → retention) |
| **1: Principal Preferences** | 1 week | Phase 0 | Indirect (stickiness) |
| **2: Decision Memos** | 1 week | Phase 0 | Direct (EA conversion feature) |
| **3: Commission Tracking** | 2 weeks | Deal Pipeline Phase 1 (done) | **Direct revenue** |
| **4: Vendor Trust** | 2 weeks | Phase 6 PRDs (exist) | Enables high-value deals |
| **5: White-Label** | TBD | Phases 1-4 | New revenue channel |

**Recommended order:** 0 → 3 → 2 → 1 → 4 → 5

Rationale: Phase 3 (commission tracking) is the revenue engine and builds directly on the Deal Pipeline you just shipped. Phase 2 (memos) is the EA hook. Phase 1 (preferences) makes the product sticky but isn't urgent for launch.

---

## Key Architecture Decisions

1. **No separate vector store.** pgvector handles vendor embeddings. User preferences are structured key-value pairs in `UserPreference`, not embeddings. If free-text preference recall becomes important later, embed them into the same pgvector-backed table.

2. **No Pinecone/Weaviate.** The research doc suggests these but they add infrastructure cost and complexity. pgvector on your existing Postgres handles the current scale (3,000 vendors) easily.

3. **PDF generation on frontend.** `@react-pdf/renderer` or `html2canvas` + `jsPDF` avoids adding a heavy Python dependency. The backend provides structured JSON; the frontend renders it.

4. **Commission tracking is manual-first.** Don't over-automate commission collection before you have vendor relationships. Start with admin dashboard + manual invoicing via Stripe. Automate after patterns emerge.

5. **Row-Level Security deferred.** RLS is important for multi-tenant Family Office isolation but premature for a single-tenant MVP. Add when the second paying organization onboards.

---

## Open Questions (Need Your Input)

1. **Which vertical first?** The research doc covers jets, yachts, diamonds, estates, and travel. Pick ONE for the first 10 vendor relationships. Recommendation: **private aviation** — you already have `service_category: "private_aviation"` in the LLM, and charter is a repeatable, high-commission transaction.

2. **Commission rate defaults?** Currently `Vendor.default_commission_rate = 0.05` (5%). The research doc suggests 10-15% for travel, 5-10% for charters, 1-3% for asset sales. Should we make this category-dependent?

3. **Decision Memo branding?** Should it say "BuyAnything" or should it be unbranded/white-labelable from day one?

4. **Phase 3 before Phase 2?** I recommended this for revenue-first, but if you're pitching to EAs soon, the memo feature might be more impressive for demos.
