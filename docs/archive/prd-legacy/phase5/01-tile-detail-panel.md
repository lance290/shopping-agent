# PRD: Tile Detail Panel (Frontend)

**Status:** Not built (backend exists)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P1  
**Origin:** Expanded PRD Acceptance Criteria ("Clicking a tile must open a standardized detail view"), GAP-ANALYSIS P1

---

## Problem Statement

The expanded PRD requires: *"Clicking a tile must open a standardized detail view that includes the choice-factor highlights and the relevant Q&A/chat log."* The backend `BidWithProvenance` endpoint exists and returns structured provenance data (`matched_features`, `chat_excerpts`, `product_info`), but **no frontend panel renders it**. Users cannot see why a tile was recommended, what choice factors it matches, or its score breakdown.

**Current state:**
- Backend: `GET /rows/{row_id}/bids/{bid_id}/provenance` returns `BidWithProvenance` with structured data.
- Frontend: `useDetailPanelStore` exists in `OfferTile.tsx` but the panel component is not implemented.
- Scoring data is stored in `provenance.score` (from `sourcing/scorer.py`) but never displayed.

---

## Requirements

### R1: Detail Panel Component (P0)

Slide-out or modal panel that displays full tile details.

**Content sections:**
1. **Product info** — Image, title, price, merchant, rating/reviews, shipping, condition
2. **Choice-factor match** — Which of the buyer's stated requirements this offer satisfies
3. **Score breakdown** — `price_score`, `relevance_score`, `quality_score`, `diversity_bonus`, `combined_score` (from PRD 11)
4. **Provenance** — Which search provider found this, when, raw source data summary
5. **Chat excerpts** — Relevant Q&A from the conversation that led to this result

**Acceptance criteria:**
- [ ] Panel opens when user clicks a tile (or clicks "Details" on a tile)
- [ ] All 5 content sections render when data is available
- [ ] Graceful fallback when sections have no data (e.g., "No chat excerpts available")
- [ ] Panel is dismissible (click outside, X button, Escape key)
- [ ] Mobile-responsive (full-screen on mobile, slide-out on desktop)

### R2: Score Explainability (P1)

Show why this tile ranks where it does.

**Display:**
- Bar chart or progress bars for each score dimension
- Combined score as a percentage or star rating
- Tooltip explaining each dimension (e.g., "Price score: how well this fits your budget")

**Acceptance criteria:**
- [ ] Score breakdown visible in detail panel
- [ ] Each dimension labeled with human-readable explanation
- [ ] Combined score prominently displayed

### R3: Choice-Factor Highlights (P1)

Show which choice factors this offer matches.

**Display:**
- List of buyer's choice factors with checkmarks/crosses
- Matched values highlighted (e.g., "Frame material: ✅ Carbon")
- Unmatched or unknown factors shown as gray/neutral

**Acceptance criteria:**
- [ ] Choice factors from `row.choice_answers` displayed
- [ ] Match status per factor shown (matched/unmatched/unknown)
- [ ] Factors sourced from `BidWithProvenance.matched_features`

### R4: Provenance Trail (P2)

Show where this result came from.

**Display:**
- Source provider (e.g., "Google Shopping via SerpAPI")
- When it was found (timestamp)
- Whether affiliate link applies (handler name)
- Link to original listing (canonical URL)

**Acceptance criteria:**
- [ ] Source provider displayed with icon/label
- [ ] Timestamp shown as relative time ("2 hours ago")
- [ ] Canonical URL available as "View original listing" link

---

## Technical Implementation

### Frontend

**New files:**
- `apps/frontend/app/components/TileDetailPanel.tsx` — Main panel component
- `apps/frontend/app/components/ScoreBreakdown.tsx` — Score visualization

**Modified files:**
- `apps/frontend/app/components/OfferTile.tsx` — Wire click handler to open panel
- `apps/frontend/app/store.ts` — Add detail panel state (or use existing `useDetailPanelStore`)

**Data flow:**
1. User clicks tile → `openPanel(bid_id, row_id)`
2. Panel fetches `GET /api/rows/{row_id}/bids/{bid_id}/provenance` via BFF proxy
3. Panel renders `BidWithProvenance` data

### Backend
- No changes required — `BidWithProvenance` endpoint already exists.

### BFF
- May need proxy route if not already present: `GET /api/rows/:rowId/bids/:bidId/provenance`

---

## Dependencies

- Phase 4 PRD 07 (workspace + tile provenance) — provides backend data
- Phase 4 PRD 11 (personalized ranking) — provides score breakdown data

---

## Effort Estimate

- **R1:** Medium (1-2 days — panel component + data fetching)
- **R2:** Small (half-day — score visualization)
- **R3:** Small (half-day — choice factor display)
- **R4:** Small (half-day — provenance trail)
