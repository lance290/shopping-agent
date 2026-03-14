# PopSavings Standalone Extraction Plan

## Objective

Extract all PopSavings code, assets, runtime dependencies, and required data from `Shopping Agent` into a new standalone repository at `/Volumes/PivotNorth/PopSavings`.

This plan assumes:

- PopSavings and BuyAnything will **not** share code.
- PopSavings and BuyAnything will **not** share data.
- Any currently shared primitive that PopSavings depends on must be **copied into PopSavings**.
- Cleanup in `Shopping Agent` happens only **after** PopSavings runs independently and has passed cutover validation.

## Non-Negotiable Rules

- **Standalone first**
  - Do not preserve runtime coupling between repos.
  - Do not introduce cross-repo imports, shared packages, or shared database reads.

- **Copy before simplify**
  - If PopSavings currently depends on shared code, copy it into PopSavings first.
  - After PopSavings runs, simplify or rename it inside the new repo.

- **No heuristic migration decisions**
  - Migration scope should be based on actual code usage and actual data relationships.
  - Do not infer ownership from naming alone.

- **Delete only after verification**
  - Remove Pop code from `Shopping Agent` only after PopSavings is fully runnable, data is migrated, and critical flows are validated.

## Current State Summary

PopSavings is already a distinct product surface, but it is embedded into the monorepo across four layers:

- **Pop-specific files**
  - Dedicated backend routes, models, frontend pages, assets, and tests.

- **Shared backend primitives used by Pop**
  - Auth/session plumbing, list/row models, bids/vendors, shared chat helpers, LLM helpers, and SDUI/search builders.

- **Shared frontend primitives used by Pop**
  - Auth utilities, API proxy utilities, shared state/store, shared modal/UI primitives, and shared dynamic rendering.

- **Shared schema pollution**
  - Pop-specific fields and tables live inside core models used by the rest of the monorepo.

## Verified Coupling That Must Be Broken By Duplication

### Backend Coupling

- `apps/backend/routes/pop_processor.py` imports and uses shared chat internals:
  - `_create_row`
  - `_update_row`
  - `_save_choice_factors`
  - `_stream_search`

- `apps/backend/routes/pop_chat.py` also depends on shared chat helper behavior.

- `apps/backend/services/llm.py` re-exports Pop decisioning from `services/llm_pop.py` instead of keeping a clean boundary.

- Pop search/list rendering flows transitively depend on shared bid/vendor/search/SDUI code.

### Schema Coupling

Pop-specific data currently leaks into shared models:

- `apps/backend/models/auth.py`
  - `wallet_balance_cents`
  - `ref_code`
  - `referred_by_id`
  - `zip_code`

- `apps/backend/models/rows.py`
  - `ProjectMember`
  - `ProjectInvite`
  - `GroupThread`

- `apps/backend/models/social.py`
  - `RowReaction`
  - `RowComment`

- `apps/backend/models/bids.py`
  - `is_swap`

### Frontend Coupling

- `apps/frontend/middleware.ts` rewrites Pop traffic into the multi-brand app.
- `apps/frontend/app/utils/brand.tsx` contains Pop and BuyAnything brand logic in one file.
- `apps/frontend/app/pop-site/layout.tsx` imports shared UI/state components.
- `apps/frontend/app/utils/auth.ts` contains Pop referral handling in shared auth code.
- Pop UI depends on shared components such as:
  - `LocationPrompt`
  - `ReportBugModal`
  - `DynamicRenderer`
  - `useShoppingStore`

## Extraction Strategy

Use a three-bucket approach:

1. **Copy as-is**
   - Files that are already Pop-specific and can move directly.

2. **Copy then refactor inside PopSavings**
   - Files that are currently shared but are required for Pop to run.

3. **Delete from Shopping Agent after cutover**
   - Pop-only code and Pop-specific branches that should be removed once Pop is live independently.

## Extraction Matrix

## 1. Copy As-Is Into `/Volumes/PivotNorth/PopSavings`

### Backend: Pop-specific routes

Copy these directly into the PopSavings backend, then rename/reorganize if needed inside the new repo:

- `apps/backend/routes/pop.py`
- `apps/backend/routes/pop_chat.py`
- `apps/backend/routes/pop_list.py`
- `apps/backend/routes/pop_offers.py`
- `apps/backend/routes/pop_wallet.py`
- `apps/backend/routes/pop_referral.py`
- `apps/backend/routes/pop_social.py`
- `apps/backend/routes/pop_swaps.py`
- `apps/backend/routes/pop_brand_portal.py`
- `apps/backend/routes/pop_notify.py`
- `apps/backend/routes/pop_processor.py`
- `apps/backend/routes/pop_helpers.py`

### Backend: Pop-specific models

- `apps/backend/models/pop.py`
- `apps/backend/models/coupons.py`

### Frontend: Pop-specific app surfaces

Copy the full Pop frontend surface:

- `apps/frontend/app/pop-site/**`
- `apps/frontend/app/api/pop/**`
- `apps/frontend/public/pop-apple-icon.png`
- `apps/frontend/public/pop-avatar.png`
- `apps/frontend/public/pop-icon-192.png`
- `apps/frontend/public/pop-icon-512.png`
- `apps/frontend/public/pop-manifest.json`

### Tests: Pop-specific tests

Copy Pop-owned test coverage with the feature:

- backend tests matching `test_pop*.py`
- backend `test_regression_pop_flows.py`
- frontend tests matching `app/tests/pop-*`
- any Pop-specific list/chat/component tests colocated under Pop surfaces

### Docs and product artifacts

Copy Pop-specific planning and reference docs needed to continue development:

- `docs/prd/pop-penny-beater/**`
- `docs/archive/pop/**`
- Pop-specific outreach/playbook/reference material as needed for the Pop team

## 2. Copy Then Refactor Inside PopSavings

These should be duplicated into PopSavings because Pop depends on them, but they should become Pop-owned code after the move.

### Backend: core application plumbing

Copy the minimum runnable backend foundation:

- `apps/backend/main.py`
- database/session/config wiring
- auth/session middleware
- dependency injection/session helpers
- environment loading and settings code
- Alembic configuration and migration wiring

### Backend: shared models Pop still needs

Copy these into PopSavings, then remove BuyAnything assumptions from them:

- `apps/backend/models/auth.py`
- `apps/backend/models/rows.py`
- `apps/backend/models/bids.py`
- vendor/search-related models used by Pop search and offers
- `apps/backend/models/social.py`
- `apps/backend/models/__init__.py`

Refactor target inside PopSavings:

- Move Pop-only schema out of shared-looking model files.
- Rename modules around Pop concepts instead of generic monorepo concepts where helpful.
- Keep only fields and tables Pop actually needs.

### Backend: shared helper/services Pop currently relies on

Copy these into PopSavings and make them internal Pop services:

- `apps/backend/routes/chat_helpers.py`
- shared search/sourcing utilities used by `_stream_search`
- `apps/backend/services/llm.py`
- `apps/backend/services/llm_pop.py`
- `apps/backend/services/llm_core.py`
- `apps/backend/services/coupon_provider.py`
- `apps/backend/services/veryfi.py`
- `apps/backend/services/sdui_builder.py`
- any shared notification/email/SMS helpers used by Pop flows

Refactor target inside PopSavings:

- Replace chat-helper imports from route modules with Pop-owned service modules.
- Keep `llm_pop.py` as Pop-local logic rather than re-exporting it from a shared hub.
- Remove any BuyAnything-only provider branches, assumptions, or DTOs.

### Frontend: shared utilities and primitives Pop needs

Copy these into PopSavings:

- `apps/frontend/app/utils/auth.ts`
- `apps/frontend/app/utils/api-proxy.ts`
- `apps/frontend/app/store.ts`
- `apps/frontend/app/store-state.ts`
- `apps/frontend/app/components/ReportBugModal.tsx`
- `apps/frontend/app/components/LocationPrompt.tsx`
- `apps/frontend/app/components/sdui/**`
- any supporting UI/types/utils required by Pop pages

Refactor target inside PopSavings:

- Remove `BrandProvider` and multi-brand abstractions.
- Make Pop the default and only brand.
- Remove BuyAnything naming from UX copy and metadata.
- Convert shared store usage into Pop-local state where it improves clarity.

### Frontend: app shell and routing

Copy and refactor:

- `apps/frontend/middleware.ts`
- `apps/frontend/app/utils/brand.tsx`

Refactor target inside PopSavings:

- Delete multi-brand domain rewrite behavior.
- Delete `brand=pop` compatibility logic.
- Flatten Pop routes into first-class application routes rather than `pop-site` inside a multi-brand shell.

## 3. Data To Copy Into PopSavings

PopSavings needs its own database and its own migrated data.

### Core entity families to migrate

- users with Pop activity
- Pop-authored or Pop-owned projects/lists
- rows belonging to those projects
- bids attached to those rows
- vendor records required to preserve Pop offer/search behavior
- wallet transactions
- receipts
- referrals
- pop swap records
- pop swap claims
- campaigns
- coupon campaign rows
- brand portal tokens
- project membership rows
- project invite rows
- group thread rows
- row reactions
- row comments

### Special migration cautions

- **Vendor dependencies**
  - Pop campaign and offer flows depend on vendor/bid relationships.
  - Pop cannot be migrated cleanly without either copying the required vendor subset or rebuilding those references in a Pop-native vendor model.

- **User fields currently stored in shared auth**
  - Pop-owned values such as wallet balance, referral code, referred-by relationships, and zip code must move with the user records that Pop keeps.

- **Swap classification state**
  - `Bid.is_swap` must migrate for any rows/bids Pop still needs, otherwise receipt/upload and offer rendering behavior will drift.

## 4. Code To Delete From Shopping Agent After Pop Cutover

Delete only after PopSavings is independently deployed, validated, and operating on its own data.

### Frontend removals

- `apps/frontend/app/pop-site/**`
- `apps/frontend/app/api/pop/**`
- `apps/frontend/public/pop-*`
- Pop-specific frontend tests
- Pop rewrite logic from `apps/frontend/middleware.ts`
- Pop branch from `apps/frontend/app/utils/brand.tsx`
- Pop referral handling from shared auth utilities

### Backend removals

- all `apps/backend/routes/pop*.py`
- `apps/backend/models/pop.py`
- `apps/backend/models/coupons.py`
- `apps/backend/services/llm_pop.py`
- `apps/backend/services/coupon_provider.py` if no longer needed by any non-Pop flow
- `apps/backend/services/veryfi.py` if no longer needed by any non-Pop flow
- Pop backend tests

### Shared schema cleanup after cutover

Remove Pop-specific schema from `Shopping Agent` once there are no remaining code paths using it:

- `User.wallet_balance_cents`
- `User.ref_code`
- `User.referred_by_id`
- `User.zip_code` if BuyAnything no longer needs it
- `ProjectMember`
- `ProjectInvite`
- `GroupThread`
- `RowReaction`
- `RowComment`
- `Bid.is_swap`

### Shared rendering/search cleanup after cutover

Remove Pop-specific logic from shared components/services that should remain BuyAnything-only after extraction:

- Pop swap tags or rendering branches in SDUI helpers
- receipt-upload rendering branches tied to Pop swap lifecycle
- Pop-only sourcing/coupon logic in any shared search/service code

## Target PopSavings Shape

After extraction, PopSavings should stop looking like a brand mode inside another product.

### Backend target shape

Example target structure:

- `apps/backend/routes/`
  - `auth.py`
  - `chat.py`
  - `lists.py`
  - `offers.py`
  - `wallet.py`
  - `referral.py`
  - `social.py`
  - `swaps.py`
  - `brand_portal.py`
  - `webhooks.py`

- `apps/backend/models/`
  - `auth.py`
  - `lists.py`
  - `offers.py`
  - `wallet.py`
  - `coupons.py`
  - `social.py`

- `apps/backend/services/`
  - `llm_core.py`
  - `decisioning.py`
  - `search_service.py`
  - `coupon_provider.py`
  - `veryfi.py`
  - `notification_service.py`
  - `sdui_builder.py`

### Frontend target shape

Example target structure:

- `apps/web/app/`
  - `page.tsx`
  - `chat/page.tsx`
  - `list/[id]/page.tsx`
  - `wallet/page.tsx`
  - `onboarding/page.tsx`
  - `invite/[token]/page.tsx`
  - `brands/claim/page.tsx`
  - `privacy/page.tsx`
  - `terms/page.tsx`

- `apps/web/components/`
  - Pop-local components only

- `apps/web/app/api/`
  - Pop-local API routes only

## Recommended Execution Phases

## Phase 1: Create a runnable fork

- Create the new repository skeleton at `/Volumes/PivotNorth/PopSavings`.
- Copy all Pop-specific files.
- Copy all shared code required for Pop to start and run locally.
- Wire Pop to its own environment, DB, migrations, and deployment settings.

**Exit criteria**

- Pop backend starts without importing code from `Shopping Agent`.
- Pop frontend starts without multi-brand runtime assumptions.
- Core env/config is local to Pop.

## Phase 2: Replace shared boundaries with Pop-owned services

- Convert shared helper dependencies into Pop-local services.
- Remove imports from generic/shared-looking monorepo modules where possible.
- Collapse route/helper/service boundaries around Pop concepts.

**Exit criteria**

- No Pop route depends on copied `chat_helpers` as a permanent compatibility layer.
- Pop decisioning, sourcing, and rendering are owned by Pop modules.

## Phase 3: Migrate data

- Create Pop-owned migrations.
- Export and import Pop-owned data sets.
- Validate referential integrity for users, projects, rows, bids, campaigns, and wallet data.

**Exit criteria**

- Pop database contains all required runtime entities.
- Core flows work against Pop DB only.

## Phase 4: Simplify product assumptions

- Remove BuyAnything naming, brand toggles, and shared-product abstractions.
- Flatten routes and page structure around Pop’s actual UX.
- Keep only the primitives Pop needs.

**Exit criteria**

- Pop reads like a standalone application, not a brand variant.

## Phase 5: Cutover and cleanup

- Validate Pop end-to-end in its own repo.
- Freeze Pop changes in `Shopping Agent` during cutover.
- Remove Pop code from `Shopping Agent`.
- Remove Pop schema from `Shopping Agent` after code removal and DB confirmation.

**Exit criteria**

- `Shopping Agent` has no active Pop code paths.
- Pop runs fully from `/Volumes/PivotNorth/PopSavings`.

## Cutover Validation Checklist

Validate these flows in the standalone Pop repo before deleting anything from `Shopping Agent`:

- auth start/verify/logout
- onboarding and zip/location capture
- Pop landing page and referral capture
- chat-driven list creation
- list item edit/update/delete
- list sharing/invites
- group thread behavior and inbound webhook routing
- offer hydration and swap classification display
- wallet and receipt upload flow
- referral activation and wallet crediting
- brand portal token flow and coupon submission
- admin swap/campaign management
- frontend rendering of Pop-specific SDUI blocks
- background email/SMS notifications used by Pop

## Known Risks

- **Hidden transitive dependencies**
  - Pop route files may import helpers that further import generic monorepo-only services.

- **Data model entanglement**
  - Vendor, bid, and campaign relationships may require more source data than the obvious Pop tables suggest.

- **Shared UI coupling**
  - Pop frontend may rely on more shared state/types than visible from page-level imports.

- **Cleanup sequencing risk**
  - Removing Pop schema from `Shopping Agent` too early can break non-obvious code paths or old migrations.

## Recommended Immediate Next Step

Build the next artifact as a file-by-file implementation checklist with four columns:

- path
- action (`copy as-is`, `copy then refactor`, `leave`, `delete after cutover`)
- reason
- blockers/dependencies

That checklist should be used as the actual execution tracker during extraction.

## Execution Checklist

Use this checklist as the live tracker while extracting PopSavings into `/Volumes/PivotNorth/PopSavings`.

### Guardrails

| ID | Task | Status | Notes |
| --- | --- | --- | --- |
| G1 | Do not modify BuyAnything runtime codepaths during extraction | In Progress | Only this planning doc in `Shopping Agent` has been updated so far. |
| G2 | Copy code into PopSavings before any refactor | In Progress | Initial copy-only extraction slices are underway. |
| G3 | Keep PopSavings fully standalone | In Progress | All copied code is being duplicated into `PopSavings`, not referenced cross-repo. |

### Phase 1A: Safe Copy Slice

| Path | Action | Status | Reason | Blockers / Dependencies |
| --- | --- | --- | --- | --- |
| `apps/backend/routes/pop.py` | copy as-is | Copied | Pop-only router aggregation | None for copied state |
| `apps/backend/routes/pop_chat.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_list.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_offers.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_wallet.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_referral.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_social.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_swaps.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_brand_portal.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_notify.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_processor.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/routes/pop_helpers.py` | copy as-is | Copied | Pop-only backend surface | None for copied state |
| `apps/backend/models/pop.py` | copy as-is | Copied | Pop-only models | None for copied state |
| `apps/backend/models/coupons.py` | copy as-is | Copied | Pop-only models | None for copied state |
| `apps/frontend/app/pop-site/**` | copy as-is | Copied | Pop-only frontend app | None for copied state |
| `apps/frontend/app/api/pop/**` | copy as-is | Copied | Pop-only frontend API proxies | None for copied state |
| `apps/frontend/public/pop-*` | copy as-is | Copied | Pop-only static assets | None for copied state |
| `docs/prd/pop-penny-beater/**` | copy as-is | Copied | Pop product requirements | None |
| `docs/archive/pop/**` | copy as-is | Copied | Pop history/context | None |

### Phase 1B: Shared Dependencies To Duplicate Next

| Path | Action | Status | Reason | Blockers / Dependencies |
| --- | --- | --- | --- | --- |
| `apps/backend/main.py` | copy then refactor | In Progress | Needed to boot backend | PopSavings copy now reduced to `auth`, `auth_profile`, and `pop`; more boot/runtime cleanup may still be needed |
| `apps/backend/routes/chat_helpers.py` | copy then refactor | Copied | Pop depends on helper internals | Replace with Pop-local services later |
| `apps/backend/models/auth.py` | copy then refactor | Copied | Pop auth/user state depends on it | Must split Pop-owned fields cleanly |
| `apps/backend/models/rows.py` | copy then refactor | Copied | Pop list/project state depends on it | Must preserve list/project/member relations |
| `apps/backend/models/bids.py` | copy then refactor | Copied | Pop offer/swap state depends on it | Includes `is_swap` |
| `apps/backend/models/social.py` | copy then refactor | Copied | Pop comments/reactions depend on it | Must remain Pop-local after copy |
| vendor/search-related models and services | copy then refactor | Pending | Pop sourcing depends on them | Need exact dependency inventory |
| `apps/backend/services/llm.py` | copy then refactor | Copied | Pop imports shared decisioning | Must remove shared-hub assumption |
| `apps/backend/services/llm_pop.py` | copy then refactor | Copied | Pop-local decisioning logic | Depends on `llm_core.py` |
| `apps/backend/services/llm_core.py` | copy then refactor | Copied | Pop LLM calls depend on it | Env/config dependency audit needed |
| `apps/backend/services/coupon_provider.py` | copy then refactor | Copied | Pop swaps/campaigns depend on it | Depends on Pop + shared offer models |
| `apps/backend/services/veryfi.py` | copy then refactor | Copied | Pop wallet/receipt scan depends on it | Env/config dependency audit needed |
| `apps/backend/services/sdui_builder.py` | copy then refactor | Copied | Pop UI schema rendering depends on it | Depends on bid/row models |
| `apps/frontend/app/utils/auth.ts` | copy then refactor | Copied | Pop frontend auth flow depends on it | Remove shared-brand assumptions |
| `apps/frontend/app/utils/api-proxy.ts` | copy then refactor | Copied | Pop frontend API calls depend on it | Repoint backend URL/config |
| `apps/frontend/app/store.ts` | copy then refactor | Copied | Pop UI uses shared state helpers | Depends on `store-state.ts` |
| `apps/frontend/app/store-state.ts` | copy then refactor | Copied | Pop UI uses shared state | Must prune BuyAnything state later |
| `apps/frontend/app/components/ReportBugModal.tsx` | copy then refactor | Copied | Imported by Pop layout | Depends on shared store today |
| `apps/frontend/app/components/LocationPrompt.tsx` | copy then refactor | Copied | Imported by Pop onboarding | Depends on auth/location utilities |
| `apps/frontend/app/components/sdui/**` | copy then refactor | Copied | Pop renders shared UI schema blocks | Must isolate Pop-only rendering |

### Immediate Execution Order

| Order | Step | Status | Notes |
| --- | --- | --- | --- |
| 1 | Create target repo skeleton under `/Volumes/PivotNorth/PopSavings` | Complete | Done |
| 2 | Copy Phase 1A Pop-only files into matching structure | Complete | Done |
| 3 | Inventory unresolved imports inside copied Pop files | Complete | First direct dependency layer identified |
| 4 | Copy Phase 1B shared dependencies into PopSavings | Complete | Direct dependency layers plus minimal auth + sourcing slices have been copied |
| 5 | Boot PopSavings locally against its own config | Complete | Backend (8001) + Frontend (3004) boot and serve all core flows |
| 6 | Data isolation (separate DB, session cookies) | Complete | Dedicated `popsavings` DB, `pop_session` cookie, guest email `guest@popsavings.com` |
| 7 | End-to-end functional validation | Complete | All 15 automated checks pass (auth, chat, sourcing, my-list, lists, wallet, referral, logout, guest) |
| 8 | BuyAnything rebrand cleanup | Complete | Defaults, fallbacks, docstrings, package name, footer, brand context all rebranded to PopSavings |

### Current Extraction Status

| Area | Status | Notes |
| --- | --- | --- |
| Pop-only routes/models/frontend/docs copied | Complete | Initial safe-copy slice is present in `/Volumes/PivotNorth/PopSavings`. |
| First shared dependency layer copied | Complete | Backend and frontend direct dependencies were duplicated into `PopSavings`. |
| Additional boot/config files copied | Complete | Included backend entrypoint/lockfiles and frontend config/lockfiles. |
| Minimal auth slice copied | Complete | `auth.py`, `auth_profile.py`, `auth_helpers.py`, `rate_limit.py`, security helpers, and audit support copied into `PopSavings`. |
| Pop backend entrypoint reduced to standalone surface | Complete | `PopSavings/apps/backend/main.py` now wires `auth`, `auth_profile`, `chat`, and `pop` routers. |
| Backend static syntax validation | Complete | `python3 -m compileall` passes. |
| Backend import validation | Complete | `uv run python -c 'import main'` succeeds. |
| Frontend validation | Complete | `pnpm exec tsc --noEmit` succeeds. |
| Live backend boot | Complete | Backend serving on `http://127.0.0.1:8001` (tmux `popsavings_220aa0__dev`). |
| Live frontend boot | Complete | Frontend serving on `http://127.0.0.1:3004` (tmux `popsavings_220aa0__worker`). |
| Database isolation | Complete | Standalone `popsavings` DB on port 5437. Fallbacks in `database.py` and `alembic/env.py` updated. |
| Session cookie isolation | Complete | Cookie renamed from `sa_session` to `pop_session` in backend + frontend. |
| Guest identity isolation | Complete | `GUEST_EMAIL` set to `guest@popsavings.com` in `dependencies.py` and `pop_chat.py`. |
| Standalone search endpoint | Complete | `/rows/{id}/search/stream` added to `routes/chat.py` with fallback bid creation. |
| BuyAnything rebrand | Complete | DB fallbacks, `main.py` title, email defaults, brand context, package name, footer, docstrings all rebranded. |
| End-to-end validation | Complete | 15/15 automated checks pass: backend health, pop health, frontend homepage, auth start/verify/cookie, auth me, chat (logged-in + guest), my-list, lists, wallet, referral, logout, post-logout, frontend pages. |

### Remaining Known Blockers Before First Boot

| Blocker | Type | Notes |
| --- | --- | --- |
| ~~End-to-end functional validation not yet exercised~~ | ~~Validation~~ | **RESOLVED** — 15/15 automated checks pass. |
| ~~Repo-local runtime env still needs confirmation~~ | ~~Environment~~ | **RESOLVED** — `.env` points to `popsavings` DB, all fallbacks updated. |

### Remaining Work (Phase 2+)

| Item | Phase | Priority | Notes |
| --- | --- | --- | --- |
| Replace `chat_helpers._stream_search` HTTP self-call with direct service call | Phase 2 | Medium | Currently works but is an unnecessary HTTP round-trip. |
| Remove BuyAnything-specific dead code (email_handoff.py, outreach templates, vendor contact modal) | Phase 2 | Low | Not called by Pop flows; safe to remove. |
| Remove BuyAnything brand config from `brand.tsx` | Phase 4 | Low | Defaults already set to Pop; BA config is dead code. |
| Remove shared components not used by Pop (OutreachQueue, VendorContactModal, AppView BA sections) | Phase 4 | Low | Copied but unused by Pop pages. |
| Pop-specific Alembic migration chain | Phase 3 | Medium | Currently using copied migrations from monorepo. |
| Production deployment config (Railway/Vercel) | Phase 5 | High | Needed before cutover. |
| Remove Pop code from Shopping Agent after cutover | Phase 5 | High | Only after PopSavings is in production. |
