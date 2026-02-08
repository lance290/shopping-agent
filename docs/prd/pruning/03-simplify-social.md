# PRD-03: Simplify Social & Sharing

**Priority:** P1 — low risk cleanup  
**Effort:** 0.5 day  
**Dependencies:** None  
**Net effect:** ~700 lines deleted, 5 likes endpoints → 1, 4 share endpoints → 2

---

## Problem

The vision doc says:

> "Can like/comment/share any tile or the whole row"

All three features exist — but likes and shares are over-engineered for a single-user product with no collaborators.

### Likes: 580 lines across 7 files for a boolean toggle

- `routes/likes.py` — 218 lines, **5 endpoints** (`POST /likes`, `DELETE /likes`, `GET /likes`, `GET /likes/counts`, `POST /likes/{bid_id}/toggle`)
- `app/api/likes/route.ts` — 117 lines (proxy for 3 of the 5 endpoints)
- `app/api/likes/counts/route.ts` — 61 lines (proxy)
- `app/api/bids/social/batch/route.ts` — 28 lines (proxy)
- `components/LikeButton.tsx` — 62 lines
- `store.ts` — ~100 lines of `BidSocialData` management, optimistic updates, `loadBidSocial`, `toggleLike`

The "like count" is always 0 or 1 because there's only one user per row. The `GET /likes/counts` endpoint returns `{f"bid_{b.id}": 1 for b in liked_bids}` — it's hardcoded to 1.

### Shares: 370 lines for a link nobody clicks

- `routes/shares.py` — 370 lines, **4 endpoints** (`POST /api/shares`, `GET /api/shares/{token}`, `GET /api/shares/{token}/content`, `GET /api/shares/{token}/metrics`)
- Share metrics track `unique_visitors`, `search_initiated_count`, `search_success_count`, `signup_conversion_count` — analytics for viral loops that don't exist yet
- `ShareSearchEvent` model — tracks when shared links trigger searches (already marked for deletion in PRD-01)

### Comments: 120 lines — already appropriate

Comments are lean: 3 endpoints (create, list, delete), simple model. **No changes needed.**

---

## Plan

### Likes: Collapse to 1 endpoint

**Delete:**
- `routes/likes.py` (entire file)
- `app/api/likes/route.ts`
- `app/api/likes/counts/route.ts`
- `app/api/bids/social/batch/route.ts`

**Add to `routes/bids.py`:**

A single toggle endpoint:

```python
@router.post("/bids/{bid_id}/like")
async def toggle_like(bid_id: int, ...):
    """Toggle like on a bid. Returns new state."""
    bid = await session.get(Bid, bid_id)
    # ... auth check via row ownership ...
    bid.is_liked = not bid.is_liked
    bid.liked_at = datetime.utcnow() if bid.is_liked else None
    await session.commit()
    return {"bid_id": bid_id, "is_liked": bid.is_liked}
```

That's ~20 lines replacing 218.

**Keep on `Bid` model:** `is_liked: bool` and `liked_at: Optional[datetime]` — these are already on the model and are the right place for this data.

**Simplify frontend:**

- `LikeButton.tsx` — change API call from `POST /api/likes` to `POST /api/bids/{id}/like`. Remove the separate "unlike" flow. (~10 lines simpler)
- `store.ts` — remove `BidSocialData` interface, `bidSocialData` state, `loadBidSocial` action, `loadBidSocialBatch` action. The `is_liked` flag is already on the `Bid`/`Offer` interface. The `toggleLike` action becomes a simple POST + local state flip. (~80 lines removed)
- Create a single frontend proxy: `app/api/bids/[id]/like/route.ts` (~15 lines)

### Shares: Keep create + resolve, delete the rest

**Keep:**
- `POST /api/shares` — create a share link (needed for "copy link to share")
- `GET /api/shares/{token}` — resolve a share link (needed for the `/share/[token]` page)

**Delete from `routes/shares.py`:**
- `GET /api/shares/{token}/content` — redundant with resolve endpoint
- `GET /api/shares/{token}/metrics` — no analytics dashboard uses this

**Simplify `ShareLink` model:**

Remove these columns (analytics for non-existent viral loops):
- `unique_visitors`
- `search_initiated_count`
- `search_success_count`
- `signup_conversion_count`

Keep: `token`, `resource_type`, `resource_id`, `created_by`, `permission`, `access_count`, `created_at`

**Net: ~200 lines removed from shares.py.**

---

## Files Changed

| File | Action | Lines Removed |
|---|---|---|
| `routes/likes.py` | DELETE entire file | 218 |
| `routes/bids.py` | ADD ~20 lines (toggle endpoint) | -20 |
| `routes/shares.py` | DELETE 2 endpoints + simplify | ~170 |
| `app/api/likes/route.ts` | DELETE | 117 |
| `app/api/likes/counts/route.ts` | DELETE | 61 |
| `app/api/bids/social/batch/route.ts` | DELETE | 28 |
| `app/api/bids/[id]/like/route.ts` | CREATE (~15 lines) | -15 |
| `components/LikeButton.tsx` | SIMPLIFY | ~20 |
| `store.ts` | REMOVE social data management | ~80 |
| `main.py` | REMOVE `likes_router` import + include | ~3 |
| `models.py` | REMOVE ShareLink analytics columns | ~10 |

**Net: ~670 lines removed**

---

## What Stays Unchanged

- **`routes/comments.py`** — already lean, 120 lines, 3 endpoints. Good as-is.
- **`components/CommentPanel.tsx`** — 161 lines. Appropriate.
- **`Bid.is_liked` / `Bid.liked_at`** — stays on the model. This is the right place for it.
- **`ShareLink` model** — stays, just trimmed.
- **`/share/[token]` page** — stays, still works with the 2 remaining endpoints.

---

## Verification

1. Click heart on a tile → tile shows liked state
2. Refresh page → liked state persists (it's on the Bid in Postgres)
3. Click heart again → unliked
4. Create share link → get a URL
5. Open share URL in incognito → see shared content
6. `grep -r "likes_router" apps/backend/` → zero matches
7. `pytest tests/ -x` → all pass
8. `npx next build` → frontend builds clean
