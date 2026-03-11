# PRD: BuyAnything Vendor State Indicators

## 1. Executive Summary

BuyAnything does not need a full EA dashboard for MVP, but EAs do need lightweight memory and status cues directly in the search/request experience.

This PRD defines three vendor-option states that must be visible in the row UI:

1. `Favorited` — global to the EA account across searches.
2. `Emailed` — scoped to the current search/request.
3. `Selected` — scoped to the current search/request.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Favoriting is global, and Vendor-focused
If an EA favorites a vendor, that preference should follow them across searches and projects.
**Gap Addressed:** What about non-vendors (Amazon/eBay products)? For launch, the "Rolodex" use-case dominates. Favoriting should save the Vendor to a global list. If we allow favoriting generic product URLs, they should also be stored globally in a generic bookmark table. We will replace row-local `Bid.is_liked` with global `VendorBookmark` and `ProductBookmark` logic to avoid UX confusion.

### 2.2 Emailed is per search
The UI should show whether this specific vendor was contacted for this specific row/search.

### 2.3 Selected is per search
The UI should show which option the EA selected for this specific row/search.

---

## 3. Current Problems

### 3.1 Favoriting is currently bid-local, not global
The current UI uses `toggleLikeApi` against offer/bid context (`Bid.is_liked`). This doesn't survive across different searches for the same vendor.

### 3.2 Emailed is only tracked in session-local outreach UI
Current outreach state uses local component state (`rfpSentBidIds`). Refreshing the page loses the state.

### 3.3 Selected exists but lacks prominence
`Bid.is_selected` exists but must be integrated smoothly with the new indicator hierarchy.

---

## 4. Desired Launch Behavior

### 4.1 Favorited
- Tile shows a clear favorite state.
- Favorited vendors float visually and are recognizable in later searches.
- Favorite is tied to `User x Vendor` (and `User x URL` for non-vendors), not `User x Bid`.

### 4.2 Emailed
- After outreach is sent, the tile shows `Emailed`.
- Derived from persisted outreach data (`OutreachMessage`).

### 4.3 Selected
- Highlights the selected option per row.

---

## 5. Scope

### In scope
- Replace row-local `is_liked` with global Vendor/Product favoriting.
- Define data ownership for all three states.
- Align frontend badges/controls with backend persistence.

### Out of scope
- Full CRM timelines.
- Team-shared favorites.

---

## 6. Functional Requirements

### 6.1 Global favorites
- Introduce `VendorBookmark` and `ItemBookmark` tables.
- UI language should reflect "Saved to Rolodex" or "Saved Product".

### 6.2 Per-row emailed state
- Persist emailed state through outreach records.

### 6.3 Per-row selected state
- Continue using `Bid.is_selected`.

---

## 7. Acceptance Criteria

### AC-1 Global favorite persistence
- Favorite a vendor in one row, see it favorited in a completely new search.

### AC-2 Durable emailed state
- Send outreach, refresh page, vendor still shows as emailed.

### AC-3 Durable selected state
- Select an offer, refresh the row, selected state remains visible.
