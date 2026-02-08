# Pruning Overview — What Stays, What Goes, What Simplifies

**Date:** 2026-02-08  
**Source of truth:** `need sourcing_ next ebay (3).md`  
**Audit:** `docs/ARCHITECTURE_AUDIT.md`

---

## Methodology

Every feature in the codebase was evaluated against the original vision doc. The categories:

- **KEEP** — in the vision, working, appropriately scoped
- **SIMPLIFY** — in the vision, but over-engineered for current stage
- **DEFER** — in the vision, but premature (no users/merchants/data yet)
- **DELETE** — not in the vision or so disconnected from reality it's harmful

---

## Feature Map: Vision → Code → Verdict

| # | Vision Feature | Current Implementation | Lines | Verdict |
|---|---|---|---|---|
| 1 | Chat with agent (left panel) | BFF `index.ts` + `llm.ts` + backend rows/bids | 2,231 + routes | **SIMPLIFY** — kill BFF, move to backend |
| 2 | Tiles on right (search results) | `RowStrip.tsx`, `OfferTile.tsx`, `Board.tsx`, streaming SSE | ~1,400 | **KEEP** |
| 3 | Rows grouped under projects | `Project` model, `projects.py` route, frontend | ~200 | **KEEP** |
| 4 | Choice factors (agent asks Qs) | `ChoiceFactorPanel.tsx`, `choice_factors` JSON on Row | ~500 | **KEEP** |
| 5 | Thumbs up/down tiles | `likes.py` (218 lines, 5 endpoints), `LikeButton.tsx`, store social data | ~580 | **SIMPLIFY** — collapse to PATCH on bid |
| 6 | Copy link to share | `shares.py` (370 lines, 4 endpoints), `ShareLink` + `ShareSearchEvent` models | ~500 | **SIMPLIFY** — keep create + resolve, delete metrics/analytics |
| 7 | Comments on tiles | `comments.py` (120 lines, 3 endpoints), `CommentPanel.tsx` | ~280 | **KEEP** — already lean |
| 8 | Select / lock in | `rows.py` select endpoint, bid `is_selected` flag | ~50 | **KEEP** |
| 9 | Clicks make tiles smarter | `UserSignal`, `UserPreference` models, `signals.py` route | ~250 | **KEEP** — monetization signal layer |
| 10 | Affiliate codes on ecommerce | `ClickoutEvent` model, `clickout.py` route | ~170 | **KEEP** |
| 11 | Agent sources sellers (outreach) | `outreach.py` (527 lines), `vendors.py` (729 lines), `OutreachEvent`/`SellerQuote` models | ~1,400 | **KEEP** — core differentiator |
| 12 | Seller sees buyer RFP tiles | `seller.py` (486 lines), `Merchant` model, seller pages | ~700 | **KEEP** — marketplace seller side |
| 13 | Seller bids via agent | `quotes.py` (371 lines), `SellerQuote` model, magic links | ~500 | **KEEP** — needed for outreach flow |
| 14 | Ecommerce: click and buy | `checkout.py` (396 lines), `PurchaseEvent` model | ~450 | **KEEP** — revenue path |
| 15 | B2B contracts (DocuSign) | `contracts.py` (184 lines), `Contract` model | ~250 | **KEEP** — B2B revenue path |
| 16 | Stripe Connect (seller payments) | `stripe_connect.py` (218 lines) | ~220 | **KEEP** — seller payment infrastructure |
| 17 | Notifications | `notifications.py` (147 lines), `notify.py` (164 lines), `Notification` model | ~350 | **KEEP** — needs delivery mechanism wired up |
| 18 | Bug reports | `bugs.py` (356 lines), `BugReport` model | ~400 | **SIMPLIFY** — keep minimal, or replace with GitHub Issues |
| 19 | Fraud detection | `fraud.py` (71 lines), in-memory rate limits | ~70 | **KEEP** — needs Redis upgrade, but the logic is right |
| 20 | Reputation scoring | `reputation.py` (180 lines) | ~180 | **KEEP** — needs to be wired into seller flows |
| 21 | Outreach monitor | `outreach_monitor.py` (150 lines) | ~150 | **KEEP** — needed once outreach is live |
| 22 | Admin metrics | `admin.py` route, admin pages | ~200 | **KEEP** — useful for you |
| 23 | Auth (email magic link) | `auth.py`, `AuthLoginCode`, `AuthSession`, `User` models | ~300 | **KEEP** |

---

## Summary by Action

### DELETE (~100 lines)
- `AuditLog` model (never written to anywhere in the codebase)
- `ShareSearchEvent` model (viral analytics with no tracking hooked up)

### SIMPLIFY (~3,000+ lines reduced)
- Likes: 5 endpoints → 1 PATCH
- Shares: 4 endpoints → 2 (create + resolve)
- BFF: 2,231 lines → 0 (move LLM chat to backend)
- Frontend proxy routes: 44 files → 1 catch-all
- Frontend store: 757 lines → 3 focused stores

### KEEP (everything else — this is all the product)
- Core flow: rows, bids, search, projects
- Comments, likes, shares
- Outreach + quotes (seller discovery is the product's moat)
- Clickout tracking + affiliate revenue
- Contracts (DocuSign — B2B revenue path)
- Stripe Connect (seller payments)
- Signals + preferences (personalization / learning)
- Fraud detection (needs Redis, but logic is correct)
- Reputation scoring (needs wiring into seller flows)
- Outreach monitor (needed once outreach is live)
- Notifications (needs delivery mechanism — email/push/websocket)
- Checkout + PurchaseEvent (ecommerce revenue path)
- Seller portal + merchants (marketplace seller side)
- Auth
- Admin dashboard

---

## Execution Order

| PRD | Name | Risk | Effort | Dependency |
|---|---|---|---|---|
| 01 | Minor Dead Code Cleanup | Low | 0.5 day | None |
| 02 | Kill the BFF | Medium | 2-3 days | None |
| 03 | Simplify Social & Sharing | Low | 0.5 day | None |
| 04 | Frontend Proxy Collapse + Store Split | Low | 1 day | PRD-02 |

**Total: ~4-5 days to simplify the architecture without losing any revenue features.**

PRD-02 (Kill the BFF) is the highest-impact change — eliminates an entire service and a network hop. PRD-03 and PRD-04 are cleanup that reduce maintenance burden. PRD-01 is now minimal since we're keeping all revenue infrastructure.
