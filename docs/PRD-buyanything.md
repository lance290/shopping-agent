# PRD: BuyAnything.ai — AI Agent Facilitated Marketplace (Chat + Tiles + Affiliate Clickout)

**Owner:** Product / Engineering  
**Status:** Draft  
**Version:** 0.1  
**Last updated:** 2026-01-18  
**Audience:** Product, Design, Engineering, QA, Investors

---

## TL;DR

BuyAnything.ai is an **AI agent–facilitated marketplace** where a user describes what they want to procure in chat and immediately gets a **board of tile-based options** (and later: bids) on the right. The agent converts conversation into an “RFP” (choice factors + Q&A), sources options across many providers in parallel, and routes every outbound click through a **first-party redirect + affiliate resolver** so we can reliably monetize via affiliate commissions while preserving a unified UX.

---

# 1) Problem Statement

## 1.1 What problem are we solving?

- People procure across fragmented surfaces (tabs, marketplaces, emails, local vendors).  
- Requirements gathering is tedious (choice factors differ by category).  
- Comparing options is difficult (inconsistent data: shipping, returns, ratings, photos).  
- Monetization is fragile without a first-party link strategy (affiliate attribution breaks easily).

## 1.2 Who is affected?

- **Buyers (B2C/B2B/C2C):** want a faster “tell me what to buy” workflow.  
- **Sellers/Vendors:** want qualified leads / requests, with minimal friction to respond.  
- **Operator (internal):** needs tools to manage sources, policies, and affiliate rules.

## 1.3 Why now?

- LLMs make it feasible to extract structured requirements (“RFP”) from natural language and continuously refine it.
- “Agentic orchestration” lets us fan out sourcing across many providers in parallel and unify results into one interface.

---

# 2) Vision

**“eBay for the AI agent era”**: a generic marketplace UI for anything.

- **Left:** chat with the agent.
- **Right:** rows of tiles.
- Clicking a tile shows the **FAQ / chat log** that led to that option/bid.

Two-sided dynamic views:

- **Buyer view:** tiles are seller bids/options for their needs.
- **Seller view:** tiles are buyer requests they might bid on.

---

# 3) Product Principles

- **New input takes priority:** the product is the chat+tiles marketplace, not just search.
- **Monetization is a P0:** every commerce click must be eligible for affiliate routing + tracking.
- **Unified display:** normalize images/descriptions/ratings/reviews/shipping/returns regardless of source.
- **Pluggable sourcing + pluggable affiliate:** new providers/handlers can ship weekly without rewriting frontend.

---

# 4) Core UX

## 4.1 Primary layout

- **Chat pane (left):** conversation + status (“asking choice factors”, “searching vendors”, “inviting sellers”).
- **Tiles pane (right):** rows of procurement items (each row = one procurement task).

## 4.2 Rows, projects, and indentation

- A **row** is “one thing to procure.”
- Rows can be grouped under a **project** (e.g., “Japan trip”) with indentation:
  - flights
  - hotel
  - activities
  - restaurants

## 4.3 Tiles

- **Request tile (leftmost):** what the user is buying + highlights of choice factors.
- **Option/Bid tiles (to the right):** comparable offers (or later: bids).

## 4.4 Buyer interactions (MVP target)

- Thumbs up/down a tile to reorder within a row.
- Copy link to share a tile or whole row.
- Like/comment/share (can be staged for post-MVP, but keep model hooks).
- Select a tile to “lock in” (moves left with special border).
- As the buyer clicks/reorders, ranking should improve (initially heuristic; later learned).

---

# 5) “More 2026” Sourcing: Multi-Agent vs Parallel Fetches

## 5.1 Recommendation

Do **both**, but be explicit about the boundary:

- **Parallel fetches** (deterministic, fast, cheap) should be the default for structured provider calls.
- **Multi-agent fanout** (planner + worker agents) is used to:
  - decide *which* providers to hit,
  - generate provider-specific query variants,
  - enrich/normalize missing fields,
  - and pursue long-tail vendor discovery.

This gives the investor-friendly narrative (“agent swarm”) while keeping the core system reliable.

## 5.2 Concrete architecture pattern

- **Planner (LLM):**
  - Inputs: user request + current RFP + policies.
  - Output: `SourcingPlan` (list of provider tasks + query variants + budgets/timeouts).

- **Workers (tools/tasks):**
  - Each provider search runs **in parallel** (async fanout).
  - Workers return raw results + provenance.

- **Evaluator/Normalizer (LLM or rules):**
  - Dedupes, extracts merchant domain, normalizes pricing/shipping/returns.
  - Assigns `match_score` vs choice factors.

- **Aggregator:**
  - Produces a unified list of `Offer` objects for the UI.

This can be honestly described as “an agent that spins out specialized worker agents,” even if implementation is parallel tasks under the hood.

---

# 6) Monetization: Affiliate Link Strategy (P0)

## 6.1 Non-negotiable rule

- The frontend must **never link directly** to a merchant URL.
- The frontend must link to **our clickout URL** (`click_url`) which:
  - tracks the click,
  - applies affiliate transformation,
  - redirects the user.

## 6.2 Link Resolver + Handler registry

- A `LinkResolver` routes each outbound URL to the right handler.
- Handlers are pluggable, and can grow weekly.

Resolver inputs:

- `canonical_url`
- `merchant_domain`
- `source` (google shopping, shopify, manual seller, feed)
- `context` (row_id, offer_id, user_id, campaign, etc.)

Resolver outputs:

- `final_url`
- `handler_name`
- `rewrite_applied` boolean
- `metadata` (program hints, tags, errors)

Default behavior:

- If no handler matches → `NoAffiliateHandler` (still tracks click).

## 6.3 Tracking

Minimum tracking events:

- `clickout_opened`
  - Properties: `user_id`, `row_id`, `offer_id`, `source`, `merchant_domain`, `handler_name`, `timestamp`

Future (optional):

- `conversion_reported` (if network supports postbacks)
- `revenue_attributed` (estimated/confirmed)

## 6.4 Disclosure

- Standard UI disclosure: “We may earn a commission from qualifying purchases.”

---

# 7) Personas & User Stories

## 7.1 Personas

- **Buyer:** wants fast procurement and confident selection.
- **Seller:** wants high-intent requests and an easy way to respond.
- **Operator/Admin:** manages sources, policies, affiliate rules, and quality.

## 7.2 User stories

- As a buyer, I want to describe what I need in chat so that an agent builds my RFP without forms.
- As a buyer, I want a row of comparable options so that I can decide quickly.
- As a buyer, I want to lock in a selection so that I can move on to the next procurement task.
- As a buyer, I want to share a row/tile so that collaborators can weigh in.
- As an operator, I want to manage affiliate handlers/rules so that we don’t lose commissions when sources change.

---

# 8) MVP Scope (2-week launch target)

## 8.1 MVP: Buyer-side procurement board + affiliate clickout

P0:

- Chat left + tiles right (single buyer view).
- Row creation from chat.
- Choice-factor Q&A captured as an RFP/FAQ.
- Parallel sourcing from at least 1–2 providers (starting with current Google Shopping adapter).
- Unified `Offer` model shown as tiles.
- Clickout routing through first-party redirect + tracking + resolver (even if only `NoAffiliateHandler` at launch).
- Basic disclosure.

P1 (if time):

- Row grouping under “project.”
- Thumbs up/down reorder.
- “Select” tile locks it in.
- Share link (read-only view).

Explicitly not MVP (Phase 2+):

- Seller onboarding + bidding rounds.
- Wattdata outreach.
- Docusign contract flow.
- Full reputation and anti-fraud systems.

---

# 9) Functional Requirements

## 9.1 Board + Rows

- The system shall support multiple rows per user.
- The system shall allow setting an active row context for chat actions.
- The system shall store and render “request tile” as the leftmost tile per row.

## 9.2 Choice factors / RFP

- The system shall derive choice factors from the initial user request.
- The system shall ask follow-up questions in chat to fill missing choice factors.
- The system shall store choice-factor Q&A as row-level FAQ.

## 9.3 Sourcing

- The system shall fan out provider searches in parallel.
- The system shall preserve provenance per offer (source/provider).
- The system shall normalize offer fields into a unified schema.

## 9.4 Affiliate clickout + tracking

- The system shall provide a `click_url` per offer.
- The system shall log each clickout.
- The system shall redirect to the resolved merchant URL.
- The system shall support a pluggable handler registry.

---

# 10) Data Models (TypeScript-style)

```ts
type OfferSource =
  | 'google_shopping'
  | 'shopify'
  | 'manual_seller'
  | `feed:${string}`
  | `provider:${string}`;

interface ChoiceFactor {
  name: string;
  label: string;
  type: 'select' | 'number' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}

interface Row {
  id: number;
  title: string;
  status: 'gathering_info' | 'searching' | 'has_options' | 'selected' | 'closed';
  project_id?: number;
  indent_level?: number;
  choice_factors?: ChoiceFactor[];
  choice_answers?: Record<string, string | number | boolean>;
}

interface Offer {
  id: string;
  row_id: number;
  title: string;
  price: number;
  currency: string;
  image_url: string | null;
  merchant: string;
  merchant_domain: string;
  rating: number | null;
  reviews_count: number | null;
  shipping_info: string | null;
  source: OfferSource;
  canonical_url: string;
  click_url: string;
  match_score?: number;
  highlights?: string[];
}

interface ClickoutEvent {
  id: string;
  user_id?: number;
  row_id: number;
  offer_id: string;
  canonical_url: string;
  handler_name: string;
  merchant_domain: string;
  created_at: string;
}
```

---

# 11) API Surface (conceptual)

- `POST /api/chat` (existing BFF)  
- `POST /api/search` (existing BFF proxy)

New (P0):

- `GET /api/clickout/:click_id` or `GET /api/out?offer_id=...`
  - logs click
  - resolves affiliate
  - redirects

New (P1/P2):

- `GET /rows/:row_id/offers` (persist offers vs ephemeral)
- `POST /rows/:row_id/offers/:offer_id/select`

---

# 12) Admin Strategy (bundled + restricted)

MVP recommendation:

- Keep admin UI/routes bundled.
- Restrict by server-side authorization checks.

Admin capabilities (phaseable):

- Manage provider keys/config.
- Manage domain → affiliate handler rules.
- Inspect clickout logs and revenue attribution.

---

# 13) Success Metrics

- Time to first usable options per row.
- Offer click-through rate (CTR).
- Clickout success rate (no broken redirects).
- Affiliate handler coverage (% of clicks routed to a handler vs default).
- Revenue per active user (when affiliate programs are enabled).

---

# 14) Risks & Mitigations

- **Affiliate attribution breaks as sources change**  
  - Mitigation: always route via first-party clickout; handler registry + rules.

- **Provider result quality inconsistent**  
  - Mitigation: normalization + provenance + UI disclosure.

- **Over-agentification increases cost/latency**  
  - Mitigation: parallel fetch default; only use multi-agent enrichment when needed.

---

# 15) Open Questions

- Which affiliate networks to integrate first (and which need postback tracking)?
- Do we persist offers/bids in DB in MVP or treat them as ephemeral search results per row?
- How do we define “project” UX in a minimal way (tags vs nested rows)?

---

# 16) Codebase Reality Check (2026-01-18)

## 16.1 What Already Works

| Feature | Status | Location |
|---------|--------|----------|
| Chat left + tiles right layout | ✅ Working | `frontend/app/page.tsx`, `components/Chat.tsx`, `components/Board.tsx` |
| Row creation from chat | ✅ Working | `bff/src/llm.ts` → `createRow` tool |
| Row CRUD (create/read/update/delete) | ✅ Working | `backend/main.py` → `/rows` endpoints |
| Row-scoped search | ✅ Working | `backend/main.py` → `/rows/{row_id}/search` |
| Multiple sourcing providers | ✅ Working | `backend/sourcing.py` → SerpAPI, Rainforest, ValueSerp, SearchAPI, Mock |
| Unified `SearchResult` model | ✅ Working | `backend/sourcing.py` → includes `url`, `source`, `merchant` |
| Auth + user data isolation | ✅ Working | `backend/main.py`, `models.py` → `user_id` on Row |
| Per-row result caching (frontend) | ✅ Working | `frontend/app/store.ts` → `rowResults` |

## 16.2 Critical Gaps (P0 — blocks monetization)

| Gap | Impact | Current State |
|-----|--------|---------------|
| **No clickout redirect** | Affiliate attribution impossible | `Board.tsx` links directly to `product.url` |
| **No click tracking** | Can't measure or optimize | No `ClickoutEvent` model or endpoint |
| **No affiliate resolver** | Can't transform URLs | No handler registry |
| **No `click_url` on offers** | Frontend has no redirect URL to use | `SearchResult` only has `url` |
| **No `merchant_domain` extraction** | Can't route to correct handler | Not parsing domain from URL |
| **No disclosure** | Compliance risk | No UI text |

## 16.3 Secondary Gaps (P1 — improves UX, can stage)

| Gap | Impact | Current State |
|-----|--------|---------------|
| No `choice_factors` on Row | Can't show RFP/FAQ tile | `Row` model lacks these fields |
| No project grouping | Can't indent rows under projects | No `project_id`/`indent_level` |
| No thumbs up/down | Can't reorder tiles | No UI or backend |
| No "select" lock-in | Can't mark winning offer | `Bid.is_selected` exists but not wired to ephemeral offers |
| No share link | Can't collaborate | No public/read-only route |
| Sourcing runs sequentially | Slower than needed | `search_all()` uses `for` loop, not `asyncio.gather` |

---

# 17) Implement-Next Checklist

## Sprint 1: Clickout + Tracking (P0 — do this first)

### Backend

- [ ] **1.1** Add `ClickoutEvent` model to `models.py`
  ```python
  class ClickoutEvent(SQLModel, table=True):
      id: Optional[int] = Field(default=None, primary_key=True)
      user_id: Optional[int] = Field(default=None, foreign_key="user.id")
      row_id: Optional[int] = Field(default=None)
      offer_id: str  # hash or index of the offer
      canonical_url: str
      merchant_domain: str
      handler_name: str = "none"
      created_at: datetime = Field(default_factory=datetime.utcnow)
  ```

- [ ] **1.2** Add `GET /api/out` clickout endpoint to `main.py`
  - Accept query params: `url`, `row_id`, `offer_idx`, `source`
  - Extract `merchant_domain` from URL
  - Log `ClickoutEvent`
  - Return 302 redirect to `canonical_url` (affiliate transform later)

- [ ] **1.3** Add utility `extract_merchant_domain(url: str) -> str` to `sourcing.py`

- [ ] **1.4** Extend `SearchResult` with `merchant_domain` field (computed on creation)

### BFF

- [ ] **1.5** Proxy `/api/out` to backend (or implement directly in BFF if simpler)

### Frontend

- [ ] **1.6** Update `Board.tsx`: change `href={product.url}` to `href={buildClickoutUrl(product, rowId, idx)}`
  - Helper: `buildClickoutUrl(product, rowId, idx) => /api/out?url=...&row_id=...&offer_idx=...&source=...`

- [ ] **1.7** Add disclosure text to `Board.tsx` (footer or above tiles)
  - Text: "We may earn a commission from qualifying purchases."

### Alembic Migration

- [ ] **1.8** Create migration for `ClickoutEvent` table

---

## Sprint 2: Affiliate Handler Registry (P0 — enables revenue)

### Backend

- [ ] **2.1** Create `affiliate.py` with:
  - `AffiliateHandler` abstract base class
  - `NoAffiliateHandler` (default, returns URL unchanged)
  - `LinkResolver` class with handler registry + routing rules
  - `resolve(canonical_url, merchant_domain, context) -> ResolvedLink`

- [ ] **2.2** Integrate resolver into `/api/out` endpoint
  - Call `resolver.resolve()` before redirect
  - Log `handler_name` in `ClickoutEvent`

- [ ] **2.3** Add config table or env-based rules for domain → handler mapping

### Future handlers (stub now, implement per-network):

- [ ] **2.4** `AmazonAssociatesHandler` (tag param)
- [ ] **2.5** `EbayPartnerHandler` (rover link)
- [ ] **2.6** `SkimlinksHandler` (universal fallback)

---

## Sprint 3: Parallel Sourcing (P1 — improves speed)

### Backend

- [ ] **3.1** Refactor `SourcingRepository.search_all()` to use `asyncio.gather()`
  ```python
  async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
      tasks = [provider.search(query, **kwargs) for provider in self.providers.values()]
      results_lists = await asyncio.gather(*tasks, return_exceptions=True)
      # flatten and filter
  ```

- [ ] **3.2** Add per-provider timeout (e.g., 3s) to avoid slow providers blocking

---

## Sprint 4: Choice Factors + Request Tile (P1 — improves UX)

### Backend

- [ ] **4.1** Add `choice_factors: Optional[str]` and `choice_answers: Optional[str]` to `Row` model (JSON strings)

- [ ] **4.2** Alembic migration for new Row columns

### BFF

- [ ] **4.3** Add `getChoiceFactors` LLM tool that:
  - Takes a product category/query
  - Returns structured choice factors (LLM-generated)

- [ ] **4.4** Update `createRow` tool to optionally accept initial choice factors

### Frontend

- [ ] **4.5** Create `RequestTile` component (leftmost tile per row)
  - Shows title + choice factor highlights
  - Click opens FAQ/detail panel

- [ ] **4.6** Refactor `Board.tsx` to render `RequestTile` + `OptionTile[]` per row

---

## Sprint 5: Tile Interactions (P1 — improves engagement)

- [ ] **5.1** Thumbs up/down: reorder tiles client-side (store preference)
- [ ] **5.2** "Select" button: mark a tile as chosen (visual lock-in)
- [ ] **5.3** Share link: generate read-only URL for a row

---

## Deferred (Phase 2+)

- Seller onboarding + bidding
- Wattdata outreach integration
- Docusign contract flow
- Project grouping / indentation
- Admin dashboard UI
- Conversion tracking postbacks

---

# 18) Quick Reference: Key Files to Modify

| File | Changes Needed |
|------|----------------|
| `apps/backend/models.py` | Add `ClickoutEvent`, extend `Row` with choice factors |
| `apps/backend/main.py` | Add `/api/out` endpoint |
| `apps/backend/sourcing.py` | Add `merchant_domain`, parallel `asyncio.gather` |
| `apps/backend/affiliate.py` | **New file**: handler registry + resolver |
| `apps/bff/src/index.ts` | Proxy `/api/out` (or implement there) |
| `apps/frontend/app/components/Board.tsx` | Change `href` to clickout URL, add disclosure |
| `apps/frontend/app/store.ts` | (minor) Add any new offer fields |
| `alembic/versions/` | Migration for `ClickoutEvent` table |
