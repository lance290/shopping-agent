<!-- PLAN_APPROVAL: approved by USER at 2026-01-23T04:59:00Z -->

# Plan — enhancement-marketplace-pivot

## Scope of this plan
This plan covers all 6 `marketplace-pivot` PRD slices under `docs/prd/marketplace-pivot/` within a single coherent implementation roadmap, aligned to:
- Product North Star: `.cfoi/branches/main/product-north-star.md`
- Effort North Star: `.cfoi/branches/main/efforts/enhancement-marketplace-pivot/product-north-star.md`

## Inputs (authoritative requirements)
- `docs/prd/marketplace-pivot/prd-ai-procurement-agent.md`
- `docs/prd/marketplace-pivot/prd-workspace-tile-provenance.md`
- `docs/prd/marketplace-pivot/prd-multi-channel-sourcing-outreach.md`
- `docs/prd/marketplace-pivot/prd-seller-tiles-quote-intake.md`
- `docs/prd/marketplace-pivot/prd-unified-closing-layer.md`
- `docs/prd/marketplace-pivot/prd-viral-growth-flywheel.md`

## Decisions locked (from clarifying questions)
- Ship order: Yes (agent → workspace → sourcing/outreach → seller quote intake → closing → viral)
- Unified closing MVP: A = clickout / handoff only (no Stripe/DocuSign in first shipping milestone)
  - Note: Stripe/DocuSign remain in-scope for the Unified Closing slice PRD, but are intentionally deferred by this plan as a scope reduction for MVP sequencing.
- Seller access model: MVP is invite-only; design so a discoverable seller feed can be added later
- Reputation: B = lightweight reputation signals (e.g., response speed, past conversions, buyer feedback) — keep as optional and additive

## Current codebase reality (starting point)
This plan is grounded in the existing implementation:
- Frontend split-pane layout: `apps/frontend/app/page.tsx`
- Chat flow: `apps/frontend/app/components/Chat.tsx` forwarding to `apps/frontend/app/api/chat/route.ts`
- Board rows/tiles UI:
  - Row strip: `apps/frontend/app/components/RowStrip.tsx`
  - Offer tiles: `apps/frontend/app/components/OfferTile.tsx`
  - Zustand store: `apps/frontend/app/store.ts`
- Backend row + bids persistence:
  - Row creation + request spec: `apps/backend/main.py` (`POST /rows`)
  - Row-scoped search persists `Bid` rows: `apps/backend/main.py` (`POST /rows/{row_id}/search`)
  - Selection endpoint: `apps/backend/main.py` (`POST /rows/{row_id}/options/{option_id}/select`)
  - Models: `apps/backend/models.py` (`Row`, `Bid`, `Seller`, `ClickoutEvent`)
- Multi-provider sourcing: `apps/backend/sourcing.py`
- Affiliate clickout + logging:
  - Frontend: `apps/frontend/app/api/clickout/route.ts`
  - Backend: `apps/backend/main.py` (`GET /api/out`) + `apps/backend/affiliate.py`

## Key gaps vs PRDs (what will be built)
- AI Procurement Agent slice: real conversational choice-factor extraction + stored RFP structure (beyond “search on message”).
- Tile detail provenance: tile click shows FAQ/chat log + choice-factor highlights (currently comment uses `window.prompt`, no provenance view).
- Social interactions: like/comment/share are currently UI-only and not persisted.
- Multi-channel sourcing+outreach: current sourcing providers exist, but no WattData outreach pipeline or quote intake.
- Seller tiles + quote intake: no seller-side view/identity, no invite-only seller link generation, no quote object persisted.
- Viral growth: no referral graph or seller→buyer prompt.

---

# Shared Foundations (applies to all slices)

## Foundation A — Domain model expansion (minimal, extensible)
- **Add/extend business entities** required across slices:
  - Project / grouping / hierarchy for rows (today: rows are flat)
  - RFP and provenance artifacts (choice factors, Q&A)
  - Comments, likes, shares with extensible visibility
  - Seller identity beyond `Seller` inferred from merchant name
  - Quote intake (seller submitted bids distinct from search-provider bids)
  - Referral attribution (viral slice)

## Foundation B — Permissions model (buyer, collaborator, seller)
- Define roles and default access rules:
  - Buyer owns projects/rows
  - Collaborator access is link-scoped (view-only vs can-comment vs can-select)
  - Seller access is invite-only by default, tied to a specific buyer need
- Ensure comment visibility can evolve later (private notes / buyer-only / seller-visible) without changing the core API contracts.

## Foundation C — Observability and event logging
- Expand “events” to cover:
  - RFP creation, tile interactions, share/link opens, seller invite opens, quote submissions
  - Maintain clickout logging as-is (`ClickoutEvent`) and add additional events rather than overloading it.

---

# Slice 1 — AI Procurement Agent + Conversational RFP Builder
PRD: `docs/prd/marketplace-pivot/prd-ai-procurement-agent.md`

## Outcome
- Conversational entry point creates a structured RFP:
  - choice factors
  - questions + answers
  - buyer-approved RFP summary
- Triggers initial sourcing and produces first tile row quickly.

## Implementation plan (high level)
- **RFP persistence**
  - Persist choice factors + answers and map to row/project.
  - Leverage existing `Row.choice_factors` / `Row.choice_answers` fields as an incremental step.
- **Agent loop integration**
  - Update chat pipeline so the agent can:
    - propose choice factors
    - ask follow-up questions
    - store answers
    - then trigger search for the row

## Verification
- Buyer can complete an RFP via Q&A and see first row of results.
- Ambiguous intents require disambiguation before results.

## Risks
- LLM hallucination: require buyer confirmation before outreach.

---

# Slice 2 — Buyer Workspace + Tile Provenance
PRD: `docs/prd/marketplace-pivot/prd-workspace-tile-provenance.md`

## Outcome
- Split-pane workspace supports:
  - project rows
  - tiles
  - thumbs/select
  - like/comment/share on tiles and rows
  - tile detail view with provenance (FAQ/chat log, choice-factor highlights)

## Implementation plan (high level)
- **Persist social interactions**
  - Replace UI-only comment prompt with persisted comments.
  - Persist likes (user + target).
  - Persist shares as events + generated share links.
- **Tile detail panel**
  - Add a tile detail UI surface.
  - Show provenance:
    - key RFP highlights
    - relevant chat/Q&A snippet
    - offer provenance (source/provider vs seller quote)

## Verification
- Likes/comments/shares work and persist.
- Tile detail shows provenance reliably.

---

# Slice 3 — Multi-Channel Sourcing + Proactive Outreach
PRD: `docs/prd/marketplace-pivot/prd-multi-channel-sourcing-outreach.md`

## Outcome
- Buyers get instant offers from providers, and the system can trigger outreach to additional sellers.

## Implementation plan (high level)
- **Instant offers**
  - Continue using existing `SourcingRepository` and row-scoped search persistence.
- **Outreach tracking**
  - Introduce an outreach entity and status lifecycle.
  - Integrate a placeholder “manual outreach” workflow first (MVP), then WattData.

## Verification
- Outreach event can be created/updated; status visible.

---

# Slice 4 — Seller Tiles + Quote Intake
PRD: `docs/prd/marketplace-pivot/prd-seller-tiles-quote-intake.md`

## Outcome
- Sellers can access buyer needs via invite-only links, comment/ask clarifying questions, and submit a quote that becomes a buyer-visible tile.

## Implementation plan (high level)
- **Invite-only access**
  - Add seller invite tokens tied to a buyer row/project.
  - Ensure access controls are enforced.
- **Quote intake**
  - Create quote submission flow (answers + links).
  - Map quote submissions to bids/tiles.
- **Design for future seller feed**
  - Ensure the data model supports discoverability filters, but do not implement feed in MVP.

## Verification
- Seller can open invite link and submit quote.
- Buyer sees quote as tile.

---

# Slice 5 — Unified Closing Layer (MVP: Clickout / Handoff)
PRD: `docs/prd/marketplace-pivot/prd-unified-closing-layer.md`

## Outcome
- Selecting a tile provides a consistent “close” action.
- MVP: clickout/handoff only, with logging and status.

## Implementation plan (high level)
- **Standardize close actions**
  - Ensure both provider offers and seller quotes can be “closed” consistently.
- **Use existing clickout**
  - Maintain `GET /api/out` and affiliate resolver.
  - Add “closing status” concept per selection so the project reflects close intent.

## Verification
- Buyer can click out from a selected tile and the system records that event.

---

# Slice 6 — Viral Growth Flywheel
PRD: `docs/prd/marketplace-pivot/prd-viral-growth-flywheel.md`

## Outcome
- Seller→buyer conversion and collaborator onboarding is measurable.

## Implementation plan (high level)
- **Referral tracking**
  - When a user arrives via share link or seller invite, record attribution.
- **Seller-as-buyer prompt**
  - After quote submission, prompt seller to post their own need.

## Verification
- Referral attribution exists and can be reported.
- Seller can post a need after quoting.

---

# Plan Deliverables

## Deliverable 1: Master implementation plan
- This document (`plan.md`) with slice-by-slice milestones, dependencies, and verification.

## Deliverable 2: Tracking initialization (post-approval)
After you approve this plan, we will initialize:
- `ERRORS.md`, `DECISIONS.md`, `ASSUMPTIONS.md`, `metrics.json`
And set `effort.json.status` to `planned`.

# Assumptions
- Existing “rows + bids” paradigm remains the core unit of procurement.
- Clickout is the MVP closing mechanism.
- Seller access begins invite-only.

# Open Questions (to resolve during /task)
- Exact “project hierarchy” representation (groups/indentation) and migration from flat rows.
- Comment visibility scope defaults and enforcement.
- What constitutes lightweight reputation signals and where they come from.

# Approval
When ready, approve by updating the marker at the top of this file.
