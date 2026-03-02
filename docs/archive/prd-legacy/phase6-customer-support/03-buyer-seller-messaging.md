# PRD 03: Buyer-Seller Messaging

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P1  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

Buyers and sellers on the platform **cannot communicate directly**. The only interaction paths are:

1. **Buyer → Seller:** Buyer sees a seller quote tile — no way to ask clarifying questions
2. **Seller → Buyer:** Seller sees an RFP in their inbox — can only submit a quote, not ask "what size?" or "when do you need it?"
3. **Post-purchase:** After a buyer selects a quote, there's no channel to coordinate delivery, share details, or resolve issues

The `Comment` model exists but is buyer-to-bid only (visible to collaborators on the project). There is no direct private messaging between buyer and seller on a specific transaction.

Without buyer-seller messaging:
- Sellers submit quotes blindly, leading to mismatched offers
- Buyers can't negotiate or ask questions before committing
- Post-purchase coordination happens outside the platform (email, phone) — losing all context
- Disputes are harder to resolve without a communication trail

---

## Solution Overview

Build a **contextual messaging system** that enables direct communication between buyers and sellers, scoped to specific transactions (rows, quotes, purchases).

Key design principle: **Messages are always tied to a context** (a row, a quote, or a purchase) — this is not general-purpose chat. This keeps conversations focused, discoverable, and auditable.

---

## Scope

### In Scope
- Direct messaging between buyer and seller within the context of a specific Row/RFP
- Message threads tied to: Row (pre-quote), SellerQuote (during quoting), PurchaseEvent (post-purchase)
- Real-time delivery via polling (WebSockets in v2)
- Read receipts (message seen timestamp)
- Email notification when new message received (configurable)
- In-app unread badge on relevant tiles/quotes
- File/image attachments in messages
- Admin visibility into message threads (for dispute evidence, trust & safety)

### Out of Scope
- General-purpose chat (user-to-user without transaction context)
- Group messaging (multi-party beyond buyer + seller)
- WebSocket real-time delivery (v1 uses polling; v2 adds WebSockets)
- Video/voice calls
- Message editing or deletion (immutable for audit trail)
- End-to-end encryption

---

## User Stories

**US-01:** As a buyer, I want to ask a seller a question about their quote before I accept it, so I can make an informed decision.

**US-02:** As a seller, I want to ask the buyer for clarification about their RFP (size, timeline, budget) before I submit a quote.

**US-03:** As a buyer, after selecting a seller's quote, I want to message them to coordinate delivery or share details.

**US-04:** As a user, I want to see an unread message badge so I know when someone has responded.

**US-05:** As a user, I want to receive an email when I get a new message so I don't have to check the app constantly.

**US-06:** As an admin, I want to view message threads between parties during dispute resolution.

---

## Business Requirements

### Authentication & Authorization
- **Send message:** Authenticated user who is either the buyer (row owner) or seller (merchant with quote on row)
- **View thread:** Only the two parties + admins
- **Admin access:** Can view any thread (for disputes and moderation)
- **Seller access gate:** Seller must have a verified merchant profile to initiate messaging

### Message Thread Scoping

Each thread is uniquely identified by:
```
(row_id, buyer_user_id, seller_merchant_id)
```

A single Row can have multiple threads (one per seller who quotes). A thread persists across the full lifecycle: pre-quote → quote → purchase → post-purchase.

### Data Requirements

**MessageThread model:**
```
id
row_id (FK row)
buyer_user_id (FK user) — the row owner
seller_merchant_id (FK merchant)

# Status
status: active | archived | blocked
last_message_at: datetime
buyer_unread_count: int (default 0)
seller_unread_count: int (default 0)

created_at, updated_at
```

**Message model:**
```
id, thread_id (FK message_thread)
sender_id (FK user)
sender_role: buyer | seller

body (text, max 5000 chars)
attachment_urls: JSON array (nullable)

# Read tracking
read_at: datetime (nullable) — when the other party read it

created_at
```

### Notification Rules

| Event | Recipient | Channel |
|-------|-----------|---------|
| New message (first in thread) | Other party | Email + in-app |
| New message (subsequent) | Other party | In-app; email only if unread > 30 min |
| Thread archived | Both parties | In-app |

Batch email digests: If a user has 3+ unread messages across threads, send a single digest email rather than individual notifications.

### Moderation

- Messages are stored immutably (no edit/delete)
- Admin can block a thread if content violates policies
- Flagged content: profanity filter on send (warn, don't block)
- Report button on messages → creates support ticket (PRD 01)

### Performance
- Send message < 300ms
- Load thread (last 50 messages) < 500ms
- Polling interval: 10 seconds (active thread), 60 seconds (background)
- Unread count check < 100ms

### UX
- Thread appears as a slide-out panel from the offer tile or quote detail
- Messages styled like a standard chat (bubbles, timestamps, sender avatars)
- Typing indicator (nice-to-have, v2)
- Mobile-optimized: full-screen thread on mobile

---

## Technical Design

### Backend

**New file:** `routes/messages.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /messages/threads` | User | List my threads (as buyer or seller) with last message preview |
| `GET /messages/threads/{id}` | User | Get thread messages (paginated, newest first) |
| `POST /messages/threads` | User | Start a new thread (requires row_id + target merchant_id or user_id) |
| `POST /messages/threads/{id}/messages` | User | Send a message |
| `POST /messages/threads/{id}/read` | User | Mark all messages as read |
| `GET /messages/unread-count` | User | Total unread across all threads |
| `GET /admin/messages/threads/{id}` | Admin | View any thread (for disputes) |
| `POST /messages/threads/{id}/block` | Admin | Block a thread |

### Frontend

| Component / Page | Description |
|-----------------|-------------|
| `MessagePanel` | Slide-out panel on offer tiles and quote detail — shows thread |
| `MessageBadge` | Unread count badge on offer tiles with active threads |
| `/messages` | Full-page message inbox (all threads) |
| `/messages/[threadId]` | Full-page thread view (mobile) |
| Seller dashboard integration | "Messages" tab on `/seller` showing threads with buyers |

### Integration Points

- **OfferTile:** "Message Seller" button (visible when seller is a registered merchant)
- **Seller Inbox:** "Message Buyer" button on RFP cards
- **Quote Detail:** Thread embedded in quote view
- **Post-Purchase:** Thread accessible from purchase confirmation and order history
- **Dispute Resolution (PRD 02):** Message thread auto-attached as evidence

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Thread creation rate (threads / quotes submitted) | > 20% |
| Message response rate (replies / messages sent) | > 60% |
| Median response time | < 4 hours |
| Quote conversion rate WITH messaging vs. WITHOUT | Messaging > 1.5x |
| User satisfaction with messaging (survey) | > 4/5 |

---

## Acceptance Criteria

- [ ] Buyer can start a message thread with a seller from an offer tile
- [ ] Seller can start a message thread with a buyer from an RFP in their inbox
- [ ] Both parties can send and receive messages within a thread
- [ ] Unread message badge appears on offer tiles with active threads
- [ ] Email notification sent for new messages (with batching for high-volume threads)
- [ ] Messages are immutable — no edit or delete
- [ ] Admin can view any message thread for dispute resolution
- [ ] Admin can block a thread that violates policies
- [ ] Message threads are scoped to (row, buyer, seller) — no cross-row leakage
- [ ] Thread history persists across the full transaction lifecycle
- [ ] Mobile: full-screen thread view with standard chat UX

---

## Dependencies
- **PRD 01 (Support Tickets):** Report message → creates ticket
- **PRD 02 (Disputes):** Message threads are dispute evidence
- **PRD 04 (Seller Verification):** Only verified sellers can initiate messaging
- **Phase 4 PRD 04 (Notifications):** In-app notification on new messages

## Risks
- **Spam** — Sellers mass-messaging buyers → rate limit: max 5 new threads per seller per day
- **Off-platform migration** — Users share phone/email to leave platform → monitor for patterns, consider masking
- **Legal** — Storing private messages has privacy implications → clear data retention policy, GDPR delete support
- **Polling overhead** — 10-second polling at scale → plan WebSocket upgrade path for v2
