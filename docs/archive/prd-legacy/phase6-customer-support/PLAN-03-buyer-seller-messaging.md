# Implementation Plan: PRD 03 — Buyer-Seller Messaging

**Status:** Draft — awaiting approval  
**Priority:** P1 (build after PRD 01, in parallel with PRD 02)  
**Estimated effort:** 2 days  
**Depends on:** PRD 01 (report message → ticket), PRD 04 (verified sellers gate)

---

## Goal

Let buyers and sellers talk to each other within the context of a specific transaction. No general-purpose chat — every thread is scoped to a (row, buyer, seller) tuple.

---

## Current State

- **Zero direct messaging.** The `Comment` model exists but is buyer→bid only, visible to project collaborators. It's not buyer↔seller communication.
- Seller quotes appear as bid tiles. Buyer has no way to ask "what size?" or "when can you deliver?" before accepting.
- After quote acceptance, coordination happens off-platform (email/phone) — losing all context.
- No `Message` or `MessageThread` model.

---

## Build Order

### Phase A: Backend Models + Migration (30 min)

**File: `apps/backend/models.py`** — add two models:

```python
class MessageThread(SQLModel, table=True):
    __tablename__ = "message_thread"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    buyer_user_id: int = Field(foreign_key="user.id", index=True)
    seller_merchant_id: int = Field(foreign_key="merchant.id", index=True)
    
    status: str = "active"  # active, archived, blocked
    last_message_at: Optional[datetime] = None
    buyer_unread_count: int = 0
    seller_unread_count: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "message"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="message_thread.id", index=True)
    sender_id: int = Field(foreign_key="user.id")
    sender_role: str  # "buyer" or "seller"
    
    body: str  # Max 5000 chars, enforced in route
    
    read_at: Optional[datetime] = None  # When the other party read it
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Unique constraint:** `(row_id, buyer_user_id, seller_merchant_id)` on `MessageThread` — one thread per buyer-seller-row combination.

**Migration:** Create `message_thread` and `message` tables.

---

### Phase B: Backend Routes (2 hours)

**New file: `apps/backend/routes/messages.py`**

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /messages/threads` | User | List my threads (as buyer or seller). Returns last message preview + unread count. |
| `POST /messages/threads` | User | Start new thread. Body: `{ row_id, merchant_id }` (buyer starts) or `{ row_id }` (seller starts, row owner is buyer). |
| `GET /messages/threads/{id}` | User (party) | Get thread messages, paginated (newest first). |
| `POST /messages/threads/{id}/messages` | User (party) | Send message. Body: `{ body }`. Max 5000 chars. |
| `POST /messages/threads/{id}/read` | User (party) | Mark all messages as read. Resets unread count. |
| `GET /messages/unread-count` | User | Total unread across all threads. |
| `GET /admin/messages/threads/{id}` | Admin | View any thread (for dispute evidence). |
| `POST /admin/messages/threads/{id}/block` | Admin | Block a thread (sets status="blocked"). |

#### Thread creation logic:
1. Check if thread already exists for this `(row_id, buyer_user_id, seller_merchant_id)`
2. If exists and active, return it
3. If doesn't exist, create new thread
4. Buyer starts thread: must own the row. Seller starts thread: must have a merchant profile.
5. **Seller must be at least `email_verified`** to initiate (PRD 04 gate)

#### Send message logic:
1. Validate sender is a party to the thread
2. Validate thread is not `blocked` or `archived`
3. Create `Message` record
4. Increment other party's `unread_count`
5. Update `thread.last_message_at`
6. Send email notification if other party has unread > 30 min (batch/debounce)
7. Create in-app notification

#### Rate limiting:
- Max 5 new threads per seller per day (anti-spam)
- Max 50 messages per user per hour
- These use the existing `check_rate_limit()` pattern

**Register in `main.py`.**

---

### Phase C: Email Notifications (30 min)

**File: `apps/backend/services/email.py`** — add:

| Function | Trigger | Content |
|----------|---------|---------|
| `send_new_message_email()` | New message, other party offline > 30 min | "You have a new message about [row title]" |

Keep it simple for v1. Batching and digest emails are v2.

---

### Phase D: Frontend — Message Components (2-3 hours)

**New file: `apps/frontend/app/components/MessagePanel.tsx`**

Slide-out panel (or modal) that shows a message thread. Reusable across:
- Offer tile ("Message Seller" button)
- Seller inbox ("Message Buyer" button)

Content:
- Header: other party name, row title
- Messages list (chat bubble style, newest at bottom, scroll to bottom)
- Reply input + send button
- "Report" link → creates support ticket

**New file: `apps/frontend/app/messages/page.tsx`**

Full-page message inbox:
- List of all threads with: other party name, row title, last message preview, unread badge, timestamp
- Click → full thread view

**New file: `apps/frontend/app/messages/[threadId]/page.tsx`**

Full-page thread view (mobile optimized):
- Chat-style message list
- Reply form
- Header with context (row title, other party)

**Update: `apps/frontend/app/components/OfferTile.tsx`**

Add "Message Seller" button on tiles where `source === "seller_quote"`. Only shows if the seller has a merchant profile.

**Update: `apps/frontend/app/seller/page.tsx`**

Add "Message Buyer" button on RFP cards in the inbox tab.

**New component: `apps/frontend/app/components/MessageBadge.tsx`**

Small unread count badge. Shown on:
- Offer tiles with active threads
- Nav item for messages page
- Seller dashboard header

---

### Phase E: Unread Count Polling (30 min)

**Frontend approach (v1):**
- Poll `GET /api/messages/unread-count` every 60 seconds when app is in foreground
- Update badge in nav/header
- When viewing a thread, poll `GET /api/messages/threads/{id}` every 10 seconds

**v2:** WebSocket upgrade. Not in scope for initial build.

---

### Phase F: Frontend Proxy Routes (15 min)

| Route file | Proxies to |
|-----------|-----------|
| `app/api/messages/threads/route.ts` | `GET, POST /messages/threads` |
| `app/api/messages/threads/[id]/route.ts` | `GET /messages/threads/{id}` |
| `app/api/messages/threads/[id]/messages/route.ts` | `POST /messages/threads/{id}/messages` |
| `app/api/messages/threads/[id]/read/route.ts` | `POST /messages/threads/{id}/read` |
| `app/api/messages/unread-count/route.ts` | `GET /messages/unread-count` |

---

### Phase G: Tests (1 hour)

**New file: `apps/backend/tests/test_messaging.py`**

| # | Test | Expected |
|---|------|----------|
| 1 | Create thread (buyer starts) | 200, thread created |
| 2 | Create thread (seller starts) | 200, thread created |
| 3 | Create duplicate thread returns existing | 200, same thread ID |
| 4 | Send message (buyer) | 200, message created, seller unread++ |
| 5 | Send message (seller) | 200, message created, buyer unread++ |
| 6 | Non-party can't view thread | 403 |
| 7 | Non-party can't send message | 403 |
| 8 | Mark as read resets unread count | 200, unread=0 |
| 9 | Unread count across threads | Correct total |
| 10 | Blocked thread rejects messages | 403, "thread is blocked" |
| 11 | Admin can view any thread | 200 |
| 12 | Admin can block thread | 200, status=blocked |
| 13 | Rate limit: too many new threads | 429 |
| 14 | Message body max length enforced | 400 if > 5000 chars |
| 15 | List threads shows last message preview | Preview text in response |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `MessageThread` + `Message` models | +35 |
| `apps/backend/routes/messages.py` | **New file** — 8 endpoints | ~300 |
| `apps/backend/services/email.py` | Add `send_new_message_email()` | +40 |
| `apps/backend/main.py` | Register messages router | +2 |
| `apps/backend/alembic/versions/p6_messaging.py` | **New file** — create tables | ~30 |
| `apps/backend/tests/test_messaging.py` | **New file** — 15 tests | ~350 |
| `apps/frontend/app/components/MessagePanel.tsx` | **New file** — slide-out chat | ~200 |
| `apps/frontend/app/components/MessageBadge.tsx` | **New file** — unread badge | ~30 |
| `apps/frontend/app/messages/page.tsx` | **New file** — inbox | ~120 |
| `apps/frontend/app/messages/[threadId]/page.tsx` | **New file** — thread view | ~150 |
| `apps/frontend/app/components/OfferTile.tsx` | Add "Message Seller" button | ~15 modified |
| `apps/frontend/app/seller/page.tsx` | Add "Message Buyer" button | ~15 modified |
| Frontend proxy routes (5 files) | **New files** | ~75 |

**Total:** ~1,360 lines across 17 files (13 new, 4 modified)

---

## Open Questions

1. **Should we add a "Messages" tab to the main app nav?** Recommendation: Yes — add to mobile bottom nav and desktop sidebar/header.
2. **Message persistence and privacy:** Messages are immutable (no edit/delete) for audit trail. Is this acceptable? (Recommendation: Yes — standard for marketplace messaging.)
3. **Off-platform migration prevention:** Should we detect phone numbers/emails in messages and warn? (Recommendation: Defer to PRD 05 Trust & Safety.)
4. **Thread archiving:** When does a thread become archived? (Recommendation: When the associated Row is closed/purchased + 30 days. Users can still view but not send new messages.)
