# PRD: Social Features Completion

**Phase:** 3 — Closing the Loop  
**Priority:** P1  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

Likes and comments were implemented in Phase 2 with full backend models, API routes, and frontend wiring. However:

- **Never verified end-to-end** — likes/comments persistence across page reload has not been click-tested.
- **No tile reordering** — the PRDs specified that liked tiles should float to the top; this was never implemented.
- **Like/comment counts** — fields exist on `Offer` interface but aren't reliably populated from the backend social data.
- **Comment visibility** — the `Comment.visibility` field defaults to `"private"` but there's no UI to toggle public/private or share comments with collaborators.
- **Social data loading** — `loadBidSocial()` is called per-bid but there's no batch loading for a row's tiles, causing N+1 fetch patterns.

---

## 2. Solution Overview

1. **Verify and fix** the existing like/comment persistence flow.
2. **Implement tile reordering** — liked tiles sort to the front within their row.
3. **Batch social data loading** — fetch likes/comments for all bids in a row in one request.
4. **Surface counts on tiles** — show like_count and comment_count badges reliably.
5. **Add share-with-collaborators** — public comments visible to anyone with a share link.

---

## 3. Scope

### In Scope
- Fix any broken persistence in like/comment flow
- Liked-first tile sorting within RowStrip
- Batch endpoint: `GET /api/bids/social?bid_ids=1,2,3`
- Like/comment count badges on OfferTile
- Comment visibility toggle (private vs. shared)
- Optimistic UI updates that survive page reload

### Out of Scope
- Threaded comments / replies (Phase 4)
- Emoji reactions beyond like (Phase 4)
- Social notifications (Phase 4)
- Dislike / thumbs-down (Phase 4)

---

## 4. User Stories

**US-01:** As a buyer, I want my liked tiles to appear first in the row so my favorites are easy to find.

**US-02:** As a buyer, I want to see how many likes and comments each tile has so I can gauge interest.

**US-03:** As a buyer sharing my board with a friend, I want my public comments visible on the share link so they can see my notes.

**US-04:** As a buyer, I want my likes to persist when I refresh the page so I don't lose my selections.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | Clicking the like button on a tile persists the like in the database. Refreshing the page shows the tile as still liked. |
| AC-02 | Liked tiles sort to the beginning of the row's offer list (after the RequestTile). |
| AC-03 | Each OfferTile shows a like count badge when count > 0. |
| AC-04 | Each OfferTile shows a comment count badge when count > 0. |
| AC-05 | Adding a comment persists it. Refreshing the page shows the comment. |
| AC-06 | Batch social data loads in one request per row (not per bid). |
| AC-07 | Comments marked "shared" are visible on the public share page. |

---

## 6. Technical Design

### 6.1 Batch Social Endpoint

**GET /api/bids/social/batch?bid_ids=1,2,3,4,5**

Response:
```json
{
  "1": { "like_count": 3, "is_liked": true, "comment_count": 1, "comments": [...] },
  "2": { "like_count": 0, "is_liked": false, "comment_count": 0, "comments": [] },
  ...
}
```

This replaces per-bid `loadBidSocial()` calls. Called once when a RowStrip mounts or becomes visible.

### 6.2 Liked-First Sorting

In `RowStrip.tsx`, when computing the display order of offers:

```typescript
const sortedOffers = useMemo(() => {
  let sorted = [...offers];

  // Apply user sort mode (price_asc, price_desc, original)
  if (sortMode === 'price_asc') {
    sorted.sort((a, b) => a.price - b.price);
  } else if (sortMode === 'price_desc') {
    sorted.sort((a, b) => b.price - a.price);
  }

  // Liked tiles float to the front (stable sort)
  sorted.sort((a, b) => {
    const aLiked = a.is_liked ? 1 : 0;
    const bLiked = b.is_liked ? 1 : 0;
    return bLiked - aLiked;
  });

  return sorted;
}, [offers, sortMode]);
```

### 6.3 Count Badges on OfferTile

In `OfferTile.tsx`, the like and comment buttons already exist. Add count badges:

```tsx
<button onClick={onToggleLike}>
  <Heart filled={isLiked} />
  {offer.like_count > 0 && <span className="badge">{offer.like_count}</span>}
</button>

<button onClick={onComment}>
  <MessageSquare />
  {offer.comment_count > 0 && <span className="badge">{offer.comment_count}</span>}
</button>
```

### 6.4 Comment Visibility

Add a toggle to the comment form:

```tsx
<select value={visibility} onChange={e => setVisibility(e.target.value)}>
  <option value="private">Only me</option>
  <option value="shared">Anyone with link</option>
</select>
```

Backend: `POST /api/comments` already accepts `visibility` field. Share page: filter comments where `visibility = "shared"`.

### 6.5 Persistence Verification

The existing flow:
1. `toggleLike()` in store → `POST /api/likes` or `DELETE /api/likes?bid_id=X` → optimistic update.
2. On page load → `loadBidSocial(bidId)` → fetches from backend → updates store.

**Potential issues to verify:**
- Is `loadBidSocial` called on initial render? (Check RowStrip useEffect)
- Does the backend return `is_liked` relative to the authenticated user?
- Is the auth token sent correctly in social data requests?

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Likes that persist across page refresh | 100% |
| Comments that persist across page refresh | 100% |
| Tiles with social data loaded (batch) | 100% of visible tiles |
| API calls reduced (batch vs. per-bid) | >80% reduction |

---

## 8. Implementation Checklist

- [ ] Create `GET /api/bids/social/batch` endpoint in `routes/bids.py`
- [ ] Replace per-bid `loadBidSocial()` with batch loading in `RowStrip.tsx`
- [ ] Add liked-first sorting in `RowStrip.tsx` offer display
- [ ] Verify like persistence end-to-end (click → refresh → still liked)
- [ ] Verify comment persistence end-to-end
- [ ] Add like_count / comment_count badges to `OfferTile.tsx`
- [ ] Add comment visibility toggle to `CommentPanel.tsx`
- [ ] Filter shared comments on share page
- [ ] Write tests for batch social endpoint
- [ ] Write tests for liked-first sorting
- [ ] Manual click-test: like tile → refresh → still liked + sorted first
