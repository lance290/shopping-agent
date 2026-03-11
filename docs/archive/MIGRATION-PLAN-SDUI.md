# Migration Plan: Unified SDUI Architecture

> **Status:** Draft  
> **Parent docs:** [PRD-Generative-UX-UI.md](./PRD-Generative-UX-UI.md) · [PRD-SDUI-Schema-Spec.md](./PRD-SDUI-Schema-Spec.md)  
> **Goal:** Merge the BuyAnything and Pop experiences into a single Chat + Vertical List **app workspace** powered by Server-Driven UI (mounted on a dedicated app route, not the public home page).

---

## 1. Current State (What Exists Today)

### Frontend — Two Separate UIs

| Surface | Route | Key Components | Layout |
|---------|-------|---------------|--------|
| **BuyAnything** | `/` (root `page.tsx`) and `/(workspace)/app` | `Board.tsx` (691 lines), `RowStrip.tsx` (559 lines), `OfferTile.tsx`, `RequestTile.tsx`, `TileDetailPanel.tsx`, `DealCard.tsx`, `ChoiceFactorPanel.tsx` | Chat pane + horizontal Netflix-style board |
| **Pop** | `/pop-site/*` | Separate `chat/page.tsx`, `list/[id]/page.tsx`, `wallet/page.tsx`, `onboarding/page.tsx` | Standalone pages, no unified layout |

- **Middleware** (`middleware.ts`) rewrites `popsavings.com` → `/pop-site/*`
- **Store** (`store.ts`) is BuyAnything-oriented: rows, projects, rowResults, rowOfferSort, horizontal-board state
- **25 components** in `app/components/` — most are BuyAnything monoliths (Board = 691 lines, RowStrip = 559 lines)

### Backend — Two Chat Pipelines

| Pipeline | Entry Point | LLM Function | Prompt Style |
|----------|------------|--------------|-------------|
| **BuyAnything** | `routes/chat.py` (SSE stream) | `make_unified_decision()` | Full desire-tier taxonomy, vendor outreach, disambiguation |
| **Pop** | `routes/pop_processor.py` → `routes/pop_chat.py` | `make_pop_decision()` | Grocery-focused, fast-add, minimal questions |

- **Shared models:** `Row`, `Bid`, `Project`, `ProjectMember` (in `models/`)
- **Pop-specific models:** `PopSwap`, `PopSwapClaim` (in `models/coupons.py`)
- **Shared sourcing:** `sourcing/repository.py` with Kroger, Rainforest, eBay, SerpAPI providers
- **No `ui_schema`** on any model today

### What's Missing for SDUI

- No `ui_schema` / `ui_schema_version` columns on `Row` or `Bid`
- No Pydantic validation schemas for SDUI blocks
- No `DynamicRenderer` component
- No SDUI primitive components
- LLM prompts don't generate `ui_schema`
- No schema observability (failure rates, fallback tracking)
- **Legacy cruft:** `intent.category` and `desire_tier` still exist on `UserIntent`, `Row`, LLM prompts, and 20+ test files — these were supposed to have been removed already

---

## 2. Target State

### Frontend — Unified Chat + Vertical List

```
┌─────────────────────────────────────────────┐
│  Chat Pane (left)  │  List Pane (right)      │
│                    │                         │
│  [messages]        │  Row 1: ▸ [SDUI blocks] │
│  [input]           │  Row 2: ▸ [SDUI blocks] │
│                    │  Row 3: ▸ [SDUI blocks] │
│                    │                         │
│                    │  [+ Add item]           │
└─────────────────────────────────────────────┘
```

- **One layout** for both brands (brand theming via `BrandProvider`)
- **Vertical list** replaces horizontal Netflix board
- **Routing constraint:** The SDUI Chat+List experience is mounted on the authenticated app workspace route (e.g., `/app`), not the public home page (`/`).
- **Each row** renders via `DynamicRenderer` reading `row.ui_schema`
- **Each bid** within a row can override UI via `bid.ui_schema`
- **Fallback:** `MinimumViableRow` renders if schema is missing/invalid

### Backend — Single Pipeline with SDUI Generation

- One unified decision engine (merge `make_pop_decision` into `make_unified_decision` with a `mode` flag)
- **No `desire_tier` or `intent.category`.** The LLM selects UI primitives directly, not classification labels.
- **LLM selects, builder hydrates:** LLM outputs a lightweight `ui_hint` (layout + block list) as part of its existing decision call. `hydrate_ui_schema(ui_hint, row, bids)` fills in field values from structured data. Deterministic fallback if `ui_hint` is missing/invalid. (See Schema Spec §8.)
- Pydantic validator strips/rejects invalid blocks before persistence
- `ui_schema` stored on `Row` and optionally on `Bid`

---

## 3. Migration Phases

### Phase 0: Foundation (No User-Visible Changes)

**Goal:** Add SDUI infrastructure without breaking anything.

| # | Task | Layer | Risk | Files Touched |
|---|------|-------|------|---------------|
| 0.1 | **Remove `desire_tier` and `intent.category`** — delete from `UserIntent` model, `Row` model, LLM prompts, all route handlers, all tests. Replace `is_service` derivation with `row.service_type is not None`. Replace `skip_web_search` with context-derived function. Replace `score_results` tier param with signal-based scoring. | Backend | Medium — touches many files but each change is mechanical | `services/llm.py`, `models/rows.py`, `routes/chat.py`, `routes/pop_processor.py`, `routes/pop_chat.py`, 10+ test files, Alembic migration to drop `desire_tier` column |
| 0.2 | Add `ui_schema` (JSONB, nullable) + `ui_schema_version` (int, default 0) to `Project`, `Row`, and `Bid` | DB | Low — nullable columns, no data loss | `models/project.py`, `models/rows.py`, `models/bids.py`, new Alembic migration |
| 0.3 | Create Pydantic SDUI validation schemas (mirrors spec) | Backend | Low — new code only | New `services/sdui_schema.py` |
| 0.4 | Create SDUI primitive React components | Frontend | Low — new code only | New `components/sdui/` directory |
| 0.5 | Create `DynamicRenderer` + `MinimumViableRow` | Frontend | Low — new code only | New `components/sdui/DynamicRenderer.tsx`, `MinimumViableRow.tsx` |

**Deliverable:** All new code exists but is not wired into any user flow.

### Phase 1: Groceries End-to-End (Pop Domain Only)

**Goal:** Pop users see SDUI-rendered grocery rows.

| # | Task | Layer | Risk | Files Touched |
|---|------|-------|------|---------------|
| 1.1 | Add `ui_hint` to Pop LLM prompt; wire `hydrate_ui_schema(ui_hint, row, bids)` into pop_processor pipeline | Backend | Medium — prompt change + new builder | `services/llm.py`, `routes/pop_processor.py`, new `services/sdui_builder.py` |
| 1.2 | Add validation + persistence of `ui_schema` on Row after build | Backend | Low | `routes/pop_processor.py`, `routes/pop_list.py` |
| 1.3 | Build unified Pop layout: Chat + Vertical List | Frontend | Medium — replaces `/pop-site/list/[id]` | `pop-site/layout.tsx`, new `pop-site/components/UnifiedView.tsx` |
| 1.4 | Wire `DynamicRenderer` into list rows (with fallback) | Frontend | Medium | `pop-site/components/UnifiedView.tsx` |
| 1.5 | Add schema failure observability | Backend | Low | `observability/metrics.py` |
| 1.6 | Add lazy bid-expand endpoint: `GET /api/bids/{id}/schema` — hydrates bid schema on-demand, caches to `Bid.ui_schema` | Backend | Low | `routes/bids.py`, `services/sdui_builder.py` |
| 1.7 | Wire Project-level schema: `hydrate_project_ui_schema(project)` called on project load + status changes | Backend | Low | `routes/pop_list.py`, `services/sdui_builder.py` |

**Deliverable:** Pop grocery items render via SDUI with list-level header (tip jar, stats). BuyAnything unchanged.

### Phase 2: BuyAnything Migration (Progressive)

**Goal:** Replace the Netflix-style board with the same vertical list.

| # | Task | Layer | Risk | Files Touched |
|---|------|-------|------|---------------|
| 2.1 | Add `ui_hint` to BuyAnything LLM prompt; wire `hydrate_ui_schema` into `routes/chat.py` SSE pipeline | Backend | Medium — prompt change | `services/llm.py`, `routes/chat.py`, `services/sdui_builder.py` |
| 2.2 | Add `ui_schema_updated` SSE event after schema build + on status transitions | Backend | Medium | `routes/chat.py` |
| 2.3 | Create unified `AppView.tsx` (Chat + Vertical List) | Frontend | High — mounted on app workspace route (e.g., `/app`) | New `components/AppView.tsx` |
| 2.4 | Feature-flag: `SDUI_ENABLED` (per-user) toggles between Board and AppView **inside app workspace only** | Frontend | Low | app-route entrypoint, env config |
| 2.5 | Wire DynamicRenderer for retail/concierge/service intents | Frontend | Medium | `components/sdui/DynamicRenderer.tsx` |

**Deliverable:** BuyAnything users can opt-in to SDUI via feature flag.

### Phase 3: Unification + Cleanup

**Goal:** Single codebase, one layout, brand theming only.

| # | Task | Layer | Risk | Files Touched |
|---|------|-------|------|---------------|
| 3.1 | Merge `make_pop_decision` + `make_unified_decision` into single engine with `mode` param | Backend | Medium | `services/llm.py` |
| 3.2 | Unify Pop routes into main routes (collapse `/pop-site/` into brand-themed `/`) | Frontend | High — routing change | `middleware.ts`, route structure |
| 3.3 | Deprecate old components | Frontend | Low | `Board.tsx`, `RowStrip.tsx`, `OfferTile.tsx` → archive |
| 3.4 | Remove feature flag, SDUI is default | Frontend | Low | `page.tsx`, env config |
| 3.5 | Update Zustand store: remove horizontal-board state, add SDUI state | Frontend | Medium | `store.ts` |

---

## 4. Component Migration Map

### Components to DEPRECATE (replaced by SDUI primitives)

| Current Component | Lines | Replaced By |
|------------------|-------|------------|
| `Board.tsx` | 691 | `AppView.tsx` (Chat + Vertical List) |
| `RowStrip.tsx` | 559 | Vertical list row + `DynamicRenderer` |
| `OfferTile.tsx` | ~300 | `DynamicRenderer` composing `ProductImage`, `PriceBlock`, `BadgeList`, `ActionRow` |
| `TileDetailPanel.tsx` | 217 | `DynamicRenderer` with expanded layout |
| `DealCard.tsx` | 333 | `DynamicRenderer` composing `PriceBlock`, `StatusBadge`, `Timeline`, `ActionRow` |
| `RequestTile.tsx` | 404 | `ChoiceFactorForm` primitive within a row header |

### Components to KEEP (not SDUI-related)

| Component | Reason |
|-----------|--------|
| `Chat.tsx` | Chat pane remains; may need minor refactoring for unified layout |
| `ReportBugModal.tsx` | Utility — brand-agnostic |
| `DiagnosticsInit.tsx` | System utility |
| `ContactForm.tsx` | Public page component |
| `CommentPanel.tsx` | Social feature, may later become SDUI primitive |
| `LikeButton.tsx` | Social feature |
| `SearchProviderToggle.tsx` | Admin/debug tool |

### New Components to CREATE

| Component | Directory | Purpose |
|-----------|-----------|---------|
| `DynamicRenderer.tsx` | `components/sdui/` | Reads `ui_schema`, renders blocks |
| `MinimumViableRow.tsx` | `components/sdui/` | Fallback when schema is missing/invalid |
| `ProductImage.tsx` | `components/sdui/` | Image with alt, badge overlay |
| `PriceBlock.tsx` | `components/sdui/` | Price display (current, was, unit, savings) |
| `DataGrid.tsx` | `components/sdui/` | Key-value pairs (specs, details) |
| `BadgeList.tsx` | `components/sdui/` | Tags/badges (organic, prime, coupon) |
| `ActionRow.tsx` | `components/sdui/` | CTA buttons (buy, claim, view) |
| `StatusBadge.tsx` | `components/sdui/` | Status indicator (pending, funded, delivered) |
| `Timeline.tsx` | `components/sdui/` | Step timeline for deals |
| `MessageList.tsx` | `components/sdui/` | Chat excerpt display |
| `FeatureList.tsx` | `components/sdui/` | Check/cross feature list |
| `ChoiceFactorForm.tsx` | `components/sdui/` | Dynamic form for choice factors |
| `ValueVector.tsx` | `components/sdui/` | "Why we recommend this" with provenance |

---

## 5. Backend Migration Map

### Models

| Model | Change | Migration |
|-------|--------|-----------|
| `Project` | Add `ui_schema: Optional[dict]`, `ui_schema_version: int = 0` | Alembic: `ALTER TABLE project ADD COLUMN ui_schema JSONB, ADD COLUMN ui_schema_version INTEGER DEFAULT 0` |
| `Row` | Add `ui_schema: Optional[dict]`, `ui_schema_version: int = 0` | Same pattern |
| `Bid` | Add `ui_schema: Optional[dict]`, `ui_schema_version: int = 0` | Same pattern. **Populated lazily on-expand, not on creation.** |

### LLM Pipeline

| Current | Target |
|---------|--------|
| `make_unified_decision()` returns `{message, intent, action}` | Returns `{message, intent, action, ui_hint}` — no `desire_tier` or `category` |
| `make_pop_decision()` returns same shape | Same — adds `ui_hint` |
| No `ui_schema` generation | `hydrate_ui_schema(ui_hint, row, bids)` called after sourcing completes. LLM picks layout + blocks; builder fills in data values. Deterministic fallback if `ui_hint` missing. |

### Routes

| Route | Change |
|-------|--------|
| `routes/chat.py` (`_stream_search`) | After sourcing, persist `ui_schema` on Row and generated bid schemas |
| `routes/pop_processor.py` | After decision, validate and persist `ui_schema` |
| `routes/pop_list.py` (item endpoints) | Return `ui_schema` in API responses |
| `routes/bids.py` | Return `ui_schema` in bid API responses; new `GET /api/bids/{id}/schema` endpoint for lazy bid-expand hydration |

### New Files

| File | Purpose |
|------|---------|
| `services/sdui_schema.py` | Pydantic models for SDUI blocks, `validate_ui_schema()`, `strip_unknown_blocks()` |
| `services/sdui_builder.py` | (Phase 1) `hydrate_ui_schema(ui_hint, row, bids)` — hydrates LLM-selected blocks with real data; includes `derive_layout_fallback()` for when `ui_hint` is missing |

---

## 6. Store (Zustand) Migration

### State to REMOVE (Phase 3)

- `rowOfferSort` — horizontal-board sort mode per row
- `moreResultsIncoming` — streaming indicator per row (replaced by SDUI loading state)
- Horizontal scroll position tracking

### State to ADD

- `expandedRowId: string | null` — which row is expanded in vertical list
- `sduiFallbackCount: number` — observability counter

### State to KEEP

- `rows`, `projects`, `activeRowId`, `rowResults` — these map directly to the new vertical list
- `currentQuery`, `isSearching` — still needed
- `selectedProviders` — still needed for search config

---

## 7. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Builder timeout / slow hydration | Degraded latency | SLA: `hydrate_ui_schema` <1ms; `GET /api/bids/{id}/schema` <50ms p99. Monitor with standard latency metrics. |
| Concurrent schema writes (e.g. status change + webhook) | Overwritten data | Optimistic locking on persistence (`WHERE id=X AND ui_schema_version=Y`); refetch and rebuild on conflict. |
| Schema drift between PRD-SDUI-Schema-Spec.md and Pydantic models | Inconsistent behavior | Single source of truth: Pydantic models ARE the spec; doc is generated/reviewed against them |
| Pop users see regression during Phase 1 | User churn | Feature flag per user; gradual rollout |
| Board.tsx deprecation breaks BuyAnything users | Lost functionality | Feature flag; old board remains default until Phase 3 |
| Removing `desire_tier` breaks downstream scoring/filtering | Search quality regression | Replace with context-derived `should_skip_web_search()` and signal-based scoring before removing column |
| Alembic migration on production DB | Downtime | Nullable columns only; zero-downtime migration |

---

## 8. Sequencing & Dependencies

```
Phase 0 ──────────────────────────────────────────────────
  0.1 Kill desire_tier + intent.category (code cleanup)
  0.2 DB Migration (add ui_schema columns)
  0.3 Pydantic schemas ──┐
  0.4 SDUI primitives ───┤ (parallel)
  0.5 DynamicRenderer ───┘
                          │
Phase 1 ──────────────────▼───────────────────────
  1.1 ui_hint in Pop prompt + builder ┐
  1.2 Pop persistence ───────────┤
  1.3 Pop unified layout ──┤ (parallel backend/frontend)
  1.4 Wire renderer ──────┘
  1.5 Observability
                          │
Phase 2 ──────────────────▼───────────────────────
  2.1 ui_hint in BA prompt + builder
  2.2 ui_schema_updated SSE event
  2.3 AppView.tsx
  2.4 Feature flag
  2.5 Wire DynamicRenderer
                          │
Phase 3 ──────────────────▼───────────────────────
  3.1 Merge LLM engines
  3.2 Unify routes
  3.3 Deprecate old components
  3.4 Remove feature flags
  3.5 Store cleanup
```

---

## 9. Success Criteria

| Phase | Metric | Target |
|-------|--------|--------|
| 0 | All new code passes tests, zero regressions | 100% existing tests pass |
| 1 | Pop grocery rows render via SDUI | >95% of rows render without fallback |
| 1 | `ui_hint` validation pass rate | >95% of LLM outputs produce valid hints; fallback covers the rest |
| 2 | BuyAnything users on SDUI (behind flag) | Feature-complete parity with Board |
| 3 | Single unified UI for both brands | Zero references to `Board.tsx` or `RowStrip.tsx` |
