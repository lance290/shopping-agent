# Technical Specification: Pop Savings V2
### The AI Grocery Savings Agent — Web-First MVP

**Version:** 2.0-draft
**Date:** 2025-02-28
**Status:** Draft
**Scope:** V2 as defined in the PRD — web chat + shared list + Kroger product enrichment + Groflo swaps + receipt scanning + affiliate tracking

---

## 1. Architecture Overview

### 1.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        popsavings.com                           │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Chat Widget  │  │  Shopping List   │  │  Brand Portal    │  │
│  │  (Pop AI)     │  │  (Items + Swaps) │  │  (Self-Serve)    │  │
│  └──────┬───────┘  └────────┬─────────┘  └────────┬─────────┘  │
│         │                   │                      │            │
└─────────┼───────────────────┼──────────────────────┼────────────┘
          │                   │                      │
          ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (Next.js API Routes)             │
│  /api/chat  /api/list  /api/auth  /api/swap  /api/receipt       │
│  /api/brand  /api/referral  /api/wallet                         │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
  │OpenAI  │ │Kroger  │ │Groflo  │ │Twilio  │ │ BullMQ     │
  │GPT-4o  │ │MCP     │ │MCP     │ │(OTP)   │ │ Job Queue  │
  └────────┘ └────────┘ └────────┘ └────────┘ └─────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │ OCR Worker   │
                                              │ Brand Outreach│
                                              │ Worker       │
                                              └──────────────┘
       │
       ▼
  ┌──────────────────────┐     ┌───────────┐
  │   PostgreSQL         │     │   Redis    │
  │   (Primary Store)    │     │   (Cache,  │
  │                      │     │   Sessions,│
  │                      │     │   BullMQ)  │
  └──────────────────────┘     └───────────┘
```

### 1.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Primary Interface** | Web app (popsavings.com) | V2 brief explicitly says "Go to popsavings.com and talk to me." SMS/Email group listening deferred to V3+. |
| **Framework** | Next.js 14 (App Router) | Single codebase for frontend + API routes. SSR for list pages (SEO for shared links). |
| **Auth** | Phone OTP via Twilio Verify | No passwords. Matches brief: "cell and confirm a code." |
| **AI** | OpenAI GPT-4o | NLU for chat, Vision for receipt OCR. Single vendor simplifies. |
| **MCP Integration** | MCP TypeScript SDK (client) | Connect to Kroger and Groflo as MCP servers. |
| **Background Jobs** | BullMQ + Redis | Receipt OCR and brand outreach are async, potentially slow. |
| **Database** | PostgreSQL (via Prisma ORM) | Relational integrity for transactions/wallets/referrals. |
| **Deployment** | Railway | Per PRD. Supports Postgres, Redis, and worker processes natively. |

### 1.3 V2 Scope Boundaries

**IN scope:**
- Web chat with Pop (conversational onboarding + item addition)
- Shopping list web UI (items, product images, PopSwaps)
- Kroger MCP for product enrichment
- Groflo MCP for swap/coupon retrieval and redemption
- Receipt photo upload + OCR validation (web upload, not SMS)
- Bob Wallet (balance tracking, no withdrawal in V2)
- Affiliate/referral link generation and tracking
- Brand portal (OTP login, propose swaps)
- Brand outreach trigger (async job, likely semi-manual in V2)

**OUT of scope (V3+):**
- SMS/MMS group listening (Twilio inbound parsing)
- Email group listening (Mailgun inbound parse)
- WhatsApp integration
- Wallet withdrawal/payout (Stripe Connect)
- Automated LinkedIn/email brand cold outreach
- Mobile native app

---

## 2. Data Model

### 2.1 Entity Relationship Diagram

```
User 1──N FamilyGroupMember N──1 FamilyGroup
User 1──N Transaction
User 1──N ClaimedSwap
User 0..1──1 User (referrer)
FamilyGroup 1──N ShoppingList
ShoppingList 1──N ListItem
ListItem 1──N PopSwap (available swaps for that item)
PopSwap N──1 Brand
ClaimedSwap N──1 PopSwap
ClaimedSwap 0..1──1 Receipt
Brand 1──N PopSwap
Brand 0..1──1 User (brand_referrer — the user account of the brand)
```

### 2.2 Table Definitions

#### `users`
```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone         VARCHAR(20) NOT NULL UNIQUE,  -- E.164 format
  display_name  VARCHAR(100),
  wallet_balance_cents  INTEGER NOT NULL DEFAULT 0,  -- stored in cents
  referrer_id   UUID REFERENCES users(id),
  ref_code      VARCHAR(20) NOT NULL UNIQUE,  -- e.g., "POP-a3x9k2"
  role          VARCHAR(20) NOT NULL DEFAULT 'consumer',  -- 'consumer' | 'brand'
  brand_email   VARCHAR(255),  -- verified corporate email for brand users
  brand_email_verified BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_ref_code ON users(ref_code);
CREATE INDEX idx_users_referrer ON users(referrer_id);
```

**Notes:**
- `wallet_balance_cents`: Integer cents to avoid floating-point issues. All monetary values stored in cents.
- `ref_code`: Auto-generated on signup. Used in copylinks: `popsavings.com/r/{ref_code}`
- `role`: A user can be both consumer and brand. Brand role unlocked by verifying `brand_email`.
- Phone is the unique identifier. No email required for consumers.

#### `family_groups`
```sql
CREATE TABLE family_groups (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          VARCHAR(100) DEFAULT 'My Family',
  owner_id      UUID NOT NULL REFERENCES users(id),
  share_code    VARCHAR(20) NOT NULL UNIQUE,  -- for family invite link
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### `family_group_members`
```sql
CREATE TABLE family_group_members (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_group_id UUID NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id),
  joined_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(family_group_id, user_id)
);
```

#### `shopping_lists`
```sql
CREATE TABLE shopping_lists (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_group_id UUID NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
  week_of       DATE NOT NULL,  -- Monday of the shopping week
  status        VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active' | 'archived'
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(family_group_id, week_of)
);
```

**Notes:**
- One active list per family per week. `week_of` is the Monday date.
- Lists auto-archive when a new week starts (cron job or lazy evaluation).

#### `list_items`
```sql
CREATE TABLE list_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shopping_list_id  UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
  added_by_user_id  UUID NOT NULL REFERENCES users(id),
  raw_text          TEXT NOT NULL,  -- "get some 2% milk"
  normalized_name   VARCHAR(255),  -- "2% Milk"
  category          VARCHAR(100),  -- "Dairy"
  kroger_product_id VARCHAR(100),  -- from Kroger MCP
  product_image_url TEXT,
  product_details   JSONB,  -- full Kroger MCP response cached
  status            VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'swapped' | 'bought' | 'removed'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_list_items_list ON list_items(shopping_list_id);
CREATE INDEX idx_list_items_category ON list_items(category);
```

#### `pop_swaps`
```sql
CREATE TABLE pop_swaps (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  list_item_id    UUID REFERENCES list_items(id) ON DELETE SET NULL,
    -- NULL if it's a general category swap not tied to a specific item
  brand_id        UUID NOT NULL REFERENCES users(id),  -- brand user
  groflo_coupon_id VARCHAR(100),  -- from Groflo MCP
  swap_product_name VARCHAR(255) NOT NULL,  -- "Heinz 57 Sauce"
  swap_product_image TEXT,
  offer_type      VARCHAR(20) NOT NULL,  -- 'coupon' | 'bogo' | 'discount'
  savings_cents   INTEGER NOT NULL,  -- e.g., 250 = $2.50
  groflo_payout_cents INTEGER,  -- what Groflo pays us per redemption
  category        VARCHAR(100) NOT NULL,
  expires_at      TIMESTAMPTZ,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  is_sponsored    BOOLEAN NOT NULL DEFAULT FALSE,  -- top slot for brand-referred users
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pop_swaps_category ON pop_swaps(category);
CREATE INDEX idx_pop_swaps_item ON pop_swaps(list_item_id);
CREATE INDEX idx_pop_swaps_brand ON pop_swaps(brand_id);
```

#### `claimed_swaps`
```sql
CREATE TABLE claimed_swaps (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pop_swap_id     UUID NOT NULL REFERENCES pop_swaps(id),
  user_id         UUID NOT NULL REFERENCES users(id),
  list_item_id    UUID NOT NULL REFERENCES list_items(id),
  status          VARCHAR(20) NOT NULL DEFAULT 'claimed',
    -- 'claimed' | 'redeemed' | 'expired' | 'rejected'
  receipt_id      UUID REFERENCES receipts(id),
  claimed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  redeemed_at     TIMESTAMPTZ,
  UNIQUE(pop_swap_id, user_id, list_item_id)  -- one claim per swap per user per item
);
```

#### `receipts`
```sql
CREATE TABLE receipts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  image_url       TEXT NOT NULL,  -- S3/R2 URL
  image_hash      VARCHAR(64) NOT NULL,  -- SHA-256 for duplicate detection
  store_name      VARCHAR(255),
  receipt_date    DATE,
  ocr_raw_text    TEXT,  -- full OCR output
  ocr_line_items  JSONB,  -- structured: [{name, price, qty}]
  ocr_status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'processing' | 'completed' | 'failed'
  processed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_receipts_hash ON receipts(image_hash);
CREATE INDEX idx_receipts_user ON receipts(user_id);
```

**Notes:**
- `image_hash`: SHA-256 of the uploaded image bytes. Unique index prevents the same receipt image from being submitted twice (fraud prevention).

#### `transactions`
```sql
CREATE TABLE transactions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  amount_cents    INTEGER NOT NULL,  -- positive = credit, negative = debit
  type

```sql
  type            VARCHAR(30) NOT NULL,
    -- 'swap_redemption' | 'referral_earning' | 'withdrawal' | 'adjustment'
  reference_id    UUID,  -- polymorphic: claimed_swap_id, referral user_id, etc.
  description     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created ON transactions(created_at);
```

#### `brand_outreach_requests`
```sql
CREATE TABLE brand_outreach_requests (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category        VARCHAR(100) NOT NULL,
  product_name    VARCHAR(255),  -- the item the consumer wants
  demand_count    INTEGER NOT NULL DEFAULT 1,  -- how many users want this category this week
  outreach_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'sent' | 'responded' | 'declined' | 'expired'
  outreach_channel VARCHAR(20),  -- 'jeremy' | 'wattdata' | 'manual_email'
  outreach_payload JSONB,  -- request/response from outreach provider
  brand_user_id   UUID REFERENCES users(id),  -- set when brand responds and signs up
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outreach_category ON brand_outreach_requests(category);
CREATE INDEX idx_outreach_status ON brand_outreach_requests(outreach_status);
```

#### `chat_sessions`
```sql
CREATE TABLE chat_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  messages        JSONB NOT NULL DEFAULT '[]',
    -- [{role: 'user'|'assistant', content: string, timestamp: string}]
  state           VARCHAR(20) NOT NULL DEFAULT 'onboarding',
    -- 'onboarding' | 'active' | 'idle'
  context         JSONB DEFAULT '{}',  -- extracted family info, preferences, etc.
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_user ON chat_sessions(user_id);
```

**Notes:**
- Chat history stored in JSONB for simplicity in V2. If message volume grows, migrate to a dedicated `chat_messages` table.
- `state` drives the conversational flow: onboarding → ask for cell → verify OTP → ask for first item → active.
- `context` stores extracted structured data (family member names, preferred store, etc.).

### 2.3 Key Constraints & Indexes Summary

| Constraint | Purpose |
|-----------|---------|
| `users.phone UNIQUE` | One account per phone number |
| `receipts.image_hash UNIQUE` | Prevent duplicate receipt submissions |
| `claimed_swaps(pop_swap_id, user_id, list_item_id) UNIQUE` | One claim per swap per user per item |
| `shopping_lists(family_group_id, week_of) UNIQUE` | One active list per family per week |
| `family_group_members(family_group_id, user_id) UNIQUE` | No duplicate memberships |

---

## 3. API Design

### 3.1 Authentication

All authenticated endpoints use a **session token** stored in an HTTP-only cookie, issued after OTP verification.

```
POST /api/auth/request-otp
  Body: { phone: "+15551234567" }
  Response: { success: true, message: "Code sent" }
  Rate limit: 3 requests per phone per 5 minutes

POST /api/auth/verify-otp
  Body: { phone: "+15551234567", code: "123456" }
  Response: {
    success: true,
    user: { id, phone, display_name, ref_code, wallet_balance_cents },
    family_group: { id, share_code } | null,
    is_new_user: boolean
  }
  Side effects:
    - Sets HTTP-only session cookie (7-day expiry, rolling)
    - If ref_code query param present, sets referrer_id on new user
    - Creates user if not exists
    - Creates default family_group if new user

POST /api/auth/logout
  Response: { success: true }
  Side effects: Clears session cookie
```

**Twilio Verify** handles OTP delivery and validation. We never store OTP codes in our database.

### 3.2 Chat API

```
POST /api/chat
  Auth: Required
  Body: { message: "I need some 2% milk and eggs" }
  Response: {
    reply: "Got it! I've added 2% Milk and Eggs to your list. Here's your updated list: ...",
    actions: [
      { type: "item_added", item: { id, normalized_name, product_image_url, category } },
      { type: "item_added", item: { id, normalized_name, product_image_url, category } }
    ],
    swaps_found: [
      { item_id, swap: { id, swap_product_name, savings_cents, offer_type } }
    ]
  }
```

**Internal flow of `POST /api/chat`:**

```
1. Load chat_session for user
2. Append user message to session.messages
3. Call OpenAI GPT-4o with system prompt + conversation history
   System prompt includes:
     - Pop's personality and rules
     - Current list state (injected as context)
     - Available tool calls: add_item, remove_item, search_product, get_swaps
4. If LLM returns tool_calls:
   a. add_item(raw_text):
      - Call Kroger MCP: search_product(raw_text) → product details
      - Insert into list_items with enriched data
      - Call Groflo MCP: search_swaps(category, normalized_name) → available swaps
      - Insert any new pop_swaps
      - Enqueue brand_outreach job if no swaps found
   b. remove_item(item_id):
      - Update list_items.status = 'removed'
   c. search_product(query):
      - Call Kroger MCP, return results for user to pick
5. Append assistant reply to session.messages
6. Save session
7. Return response
```

**Idempotency:** Each chat message is processed exactly once. The frontend generates a `client_message_id` (UUID) sent with each request. The backend deduplicates on `(user_id, client_message_id)` using Redis with a 5-minute TTL.

### 3.3 Shopping List API

```
GET /api/list/:listId
  Auth: Required (must be member of the family group)
  Response: {
    list: {
      id, week_of, status,
      items: [{
        id, normalized_name, category, product_image_url, status,
        added_by: { id, display_name },
        swaps: [{
          id, swap_product_name, swap_product_image,
          offer_type, savings_cents, is_sponsored, brand_name
        }]
      }]
    }
  }

GET /api/list/current
  Auth: Required
  Response: Same as above, returns the active list for the user's family group.
  Side effect: Creates a new list for current week if none exists.

POST /api/list/:listId/items
  Auth: Required
  Body: { raw_text: "organic bananas" }
  Response: { item: { id, normalized_name, category, product_image_url, swaps: [] } }
  Side effects:
    - Kroger MCP lookup
    - Groflo MCP swap search
    - Enqueue brand outreach if no swaps

POST /api/list/:listId/items/search
  Auth: Required
  Body: { query: "yogurt" }
  Response: {
    results: [{ kroger_product_id, name, image_url, category, price }]
  }
  Notes: Proxies to Kroger MCP. User can pick a result to add.

DELETE /api/list/:listId/items/:itemId
  Auth: Required
  Response: { success: true }
```

### 3.4 Swap & Claim API

```
POST /api/swaps/:swapId/claim
  Auth: Required
  Body: { list_item_id: "uuid" }
  Response: {
    claimed_swap: { id, status: "claimed", swap_product_name, savings_cents }
  }
  Validation:
    - User must be in the family group that owns the list item
    - Swap must be active and not expired
    - No existing claim for this (swap, user, item) tuple

GET /api/swaps/claimed
  Auth: Required
  Response: {
    claims: [{ id, swap_product_name, savings_cents, status, claimed_at }]
  }
  Notes: Returns all active claims for the current user. Used by receipt matching.
```

### 3.5 Receipt API

```
POST /api/receipts/upload
  Auth: Required
  Content-Type: multipart/form-data
  Body: { image: <file> }
  Response: {
    receipt_id: "uuid",
    status: "processing",
    message: "Got your receipt! I'm checking it now. I'll update your wallet shortly."
  }
  Validation:
    - Max file size: 10MB
    - Accepted types: image/jpeg, image/png, image/heic
    - SHA-256 hash computed; reject if duplicate exists
  Side effects:
    - Upload image to S3/R2
    - Enqueue OCR job to BullMQ

GET /api/receipts/:receiptId
  Auth: Required
  Response: {
    receipt: { id, status, store_name, receipt_date, ocr_line_items },
    redemptions: [{ claimed_swap_id, matched_line_item, savings_cents, status }]
  }
```

### 3.6 Wallet API

```
GET /api/wallet
  Auth: Required
  Response: {
    balance_cents: 1250,
    transactions: [{
      id, amount_cents, type, description, created_at
    }],
    pagination: { page, per_page, total }
  }
  Pagination: Cursor-based on created_at DESC. Default 20 per page.
```

### 3.7 Referral API

```
GET /api/referral
  Auth: Required
  Response: {
    ref_code: "POP-a3x9k2",
    family_share_link: "https://popsavings.com/f/{share_code}",
    friend_share_link: "https://popsavings.com/r/{ref_code}",
    stats: {
      total_referrals: 12,
      total_earnings_cents: 3600,
      this_week_referrals: 2
    }
  }
```

### 3.8 Brand Portal API

```
POST /api/brand/verify-email
  Auth: Required (user must be logged in with phone)
  Body: { brand_email: "pm@heinz.com" }
  Response: { success: true, message: "Verification email sent" }

POST /api/brand/confirm-email
  Auth: Required
  Body: { code: "abc123" }
  Response: { success: true, role: "brand" }
  Side effects: Sets user.brand_email_verified = true, user.role = 'brand'

POST /api/brand/swaps
  Auth: Required (brand role)
  Body: {
    category: "Condiments",
    swap_product_name: "Heinz 57 Sauce",
    swap_product_image: "https://...",
    offer_type: "bogo",
    savings_cents: 350,
    groflo_coupon_id: "groflo-abc-123",  -- from Groflo's system
    expires_at: "2025-04-01T00:00:00Z"
  }
  Response: { swap: { id, ... } }

GET /api/brand/dashboard
  Auth: Required (brand role)
  Response: {
    active_swaps: [{ id, swap_product_name, claims_count, redemptions_count }],
    demand_signals: [{ category, product_name, demand_count }],
    referral_stats: { users_driven, revenue_share_cents }
  }
```

### 3.9 Error Response Contract

All errors follow a consistent shape:

```json
{
  "error": {
    "code": "DUPLICATE_RECEIPT",
    "message": "This receipt has already been submitted.",
    "status": 409
  }
}
```

Standard error codes:

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `UNAUTHORIZED` | 401 | Missing or invalid session |
| `FORBIDDEN` | 403 | User not in family group / not brand role |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `DUPLICATE_RECEIPT` | 409 | Receipt image hash already exists |
| `DUPLICATE_CLAIM` | 409 | Swap already claimed by this user |
| `SWAP_EXPIRED` | 410 | Swap offer has expired |
| `RATE_LIMITED` | 429 | Too many requests |
| `VALIDATION_ERROR` | 422 | Bad input (includes `fields` array) |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## 4. MCP Integration Details

### 4.1 Kroger MCP

**Assumption:** Kroger MCP is an external MCP server we connect to as a client. If it doesn't exist yet, we build an MCP server that wraps the [Kroger Developer API](https://developer.kroger.com/).

**Tools we need from Kroger MCP:**

| Tool | Input | Output |
|------|-------|--------|
| `search_products` | `{ query: "2% milk", limit: 5 }` | `[{ product_id, name, brand, category, image_url, price, upc }]` |
| `get_product` | `{ product_id: "..." }` | `{ product_id, name, brand, category, image_url, price, upc, description }` |

**Integration pattern:**
```typescript
// MCP client initialization
const krogerClient = new MCPClient({
  transport: new SSETransport("https://kroger-mcp.example.com/sse"),
  // or StdioTransport if running locally
});

// Usage in item addition flow
const results = await krogerClient.callTool("search_products", {
  query: normalizedItemName,
  limit: 5
});
```

**Fallback:** If Kroger MCP is unavailable, store the item with `raw_text` only and retry enrichment via a background job. The list still functions without images/details.

### 4.2 Groflo MCP

**Assumption:** Groflo MCP is an external MCP server providing coupon/swap data and redemption confirmation.

**Tools we need from Groflo MCP:**

| Tool | Input | Output |
|------|-------|--------|
| `search_swaps` | `{ category: "Dairy", product_name: "2% Milk" }` | `[{ groflo_id, swap_product, brand, offer_type, savings_cents, expires_at }]` |
| `create_redemption` | `{ groflo_coupon_id, receipt_data: { store, date, line_items }, user_id }` | `{ redemption_id, status: "approved"|"rejected", payout_cents, reason? }` |
| `get_coupon_details` | `{ groflo_id }` | `{ full cou

pon details, terms, brand info }` |

**Integration pattern:**
```typescript
const grofloClient = new MCPClient({
  transport: new SSETransport("https://groflo-mcp.example.com/sse"),
});

// After OCR completes, attempt redemption
const result = await grofloClient.callTool("create_redemption", {
  groflo_coupon_id: claimedSwap.groflo_coupon_id,
  receipt_data: {
    store: receipt.store_name,
    date: receipt.receipt_date,
    line_items: receipt.ocr_line_items
  },
  user_id: user.id
});
```

**Fallback:** If Groflo MCP is unavailable during item addition, show items without swaps. Retry swap search via background job every 15 minutes for up to 24 hours. If Groflo is unavailable during redemption, queue the redemption attempt and retry with exponential backoff (30s, 1m, 5m, 15m, 1h — max 5 retries).

### 4.3 MCP Error Handling & Circuit Breaker

Both MCP integrations use a circuit breaker pattern:

| State | Behavior |
|-------|----------|
| **Closed** (normal) | All requests pass through. Track failure rate over 60s window. |
| **Open** (tripped) | All requests immediately return fallback. Triggered when >50% failure rate over 10+ requests in 60s. |
| **Half-Open** (recovery) | After 30s cooldown, allow 1 probe request. If success → Closed. If failure → Open. |

Implementation via `opossum` npm package wrapping each MCP client.

---

## 5. Background Jobs (BullMQ)

### 5.1 Queue Architecture

```
Redis
├── queue:receipt-ocr          (concurrency: 3)
├── queue:swap-search          (concurrency: 5)
├── queue:brand-outreach       (concurrency: 2)
├── queue:referral-payout      (concurrency: 3)
└── queue:list-archival        (concurrency: 1, cron)
```

All queues run in a separate Railway service (`worker` process) sharing the same codebase.

### 5.2 Receipt OCR Job

**Trigger:** `POST /api/receipts/upload` enqueues after S3 upload completes.

```typescript
// Job payload
{
  jobName: "receipt-ocr",
  data: {
    receipt_id: "uuid",
    user_id: "uuid",
    image_url: "https://s3.../receipt-abc.jpg"
  }
}
```

**Processing steps:**

```
1. Download image from S3/R2
2. Call OpenAI GPT-4o Vision:
   System: "Extract all line items from this grocery receipt. Return JSON:
     { store_name, date, line_items: [{ name, price_cents, quantity }] }"
   Image: <receipt image>
3. Parse response, update receipt record:
   - ocr_raw_text, ocr_line_items, store_name, receipt_date
   - ocr_status = 'completed'
4. Load all claimed_swaps for this user with status = 'claimed'
5. For each claimed swap, fuzzy-match against ocr_line_items:
   - Normalize both strings (lowercase, remove punctuation, strip common abbreviations)
   - Use Levenshtein distance with threshold ≤ 0.3 (normalized)
   - Also match on category as a secondary signal
6. For each match:
   a. Call Groflo MCP create_redemption()
   b. If approved:
      - Update claimed_swap.status = 'redeemed'
      - Update claimed_swap.receipt_id = receipt.id
      - Credit user wallet: INSERT transaction (type: 'swap_redemption')
      - UPDATE users SET wallet_balance_cents = wallet_balance_cents + savings_cents
      - Enqueue referral-payout job for this user's referrer
   c. If rejected:
      - Update claimed_swap.status = 'rejected'
      - Log reason from Groflo
7. If OCR fails (OpenAI error, unparseable):
   - ocr_status = 'failed'
   - Alert ops via webhook (Slack/Discord)
   - User sees "We couldn't read your receipt. Please try a clearer photo."
```

**Retry policy:** 3 attempts, exponential backoff (10s, 60s, 300s). Dead-letter after 3 failures.

**Timeout:** 60 seconds per job (Vision API can be slow on large receipts).

### 5.3 Swap Search Job

**Trigger:** Enqueued when an item is added and Groflo MCP is either unavailable or returns no results (retry scenario).

```typescript
{
  jobName: "swap-search",
  data: {
    list_item_id: "uuid",
    category: "Condiments",
    normalized_name: "A1 Steak Sauce"
  },
  opts: {
    attempts: 4,
    backoff: { type: "exponential", delay: 900000 } // 15 min base
  }
}
```

**Processing:** Call Groflo MCP `search_swaps`. If results found, insert into `pop_swaps` and associate with `list_item_id`. If the list item's family group has active websocket connections, push a real-time update.

### 5.4 Brand Outreach Job

**Trigger:** Enqueued when an item is added and NO swaps exist (neither from Groflo nor from existing brand bids).

```typescript
{
  jobName: "brand-outreach",
  data: {
    category: "Condiments",
    product_name: "A1 Steak Sauce",
    demand_count: 1  // incremented if multiple users want same category
  }
}
```

**Processing (V2 — semi-automated):**

```
1. Check brand_outreach_requests for existing pending request in same category
   this week. If exists, increment demand_count and skip.
2. If new category request:
   a. Insert brand_outreach_request (status: 'pending')
   b. Attempt automated outreach:
      - Call Jeremy/Wattdata API (if available) to find brand PM contacts
      - Send templated email: "A Pop Savings user is buying {product}.
        Would you like to offer a PopSwap™? Sign up at popsavings.com/brands"
      - Update status: 'sent'
   c. If no API available (V2 fallback):
      - Post to internal Slack channel: "#brand-outreach"
      - Include category, product, demand count
      - Ops team manually reaches out
      - Update status: 'sent'
```

**Deduplication:** One outreach per category per week. The `demand_count` aggregates interest.

### 5.5 Referral Payout Job

**Trigger:** Enqueued after a successful swap redemption if the user has a `referrer_id`.

```typescript
{
  jobName: "referral-payout",
  data: {
    user_id: "uuid",          // the user who redeemed
    referrer_id: "uuid",      // who referred them
    redemption_amount_cents: 100,  // $1.00 revenue from this redemption
    payout_percentage: 30
  }
}
```

**Processing:**

```
1. Calculate payout: redemption_amount_cents * 0.30 = 30 cents
2. INSERT transaction for referrer (type: 'referral_earning', amount: 30)
3. UPDATE users SET wallet_balance_cents += 30 WHERE id = referrer_id
4. Check if referrer is a brand user:
   - If yes, also check if the redeemed swap was from this brand
   - Log for brand dashboard analytics
```

**Idempotency:** Unique constraint on `(claimed_swap_id, referrer_id)` in a `referral_payouts` tracking table prevents double-paying.

### 5.6 List Archival Cron

**Schedule:** Every Monday at 00:00 UTC.

```
1. SELECT all shopping_lists WHERE status = 'active' AND week_of < current_monday
2. UPDATE status = 'archived'
3. For each archived list's family_group, create new list for current week
   (lazy — or let GET /api/list/current handle it)
```

---

## 6. Real-Time Updates

### 6.1 Approach

**Server-Sent Events (SSE)** from the Next.js backend to the web frontend. Chosen over WebSockets for simplicity on Railway (no sticky sessions needed for SSE with proper configuration).

```
GET /api/events/list/:listId
  Auth: Required (session cookie)
  Response: text/event-stream

  Events:
    event: item_added
    data: { item: { id, normalized_name, product_image_url, category } }

    event: swap_found
    data: { item_id, swap: { id, swap_product_name, savings_cents } }

    event: item_claimed
    data: { item_id, swap_id, claimed_by: { display_name } }

    event: receipt_processed
    data: { receipt_id, redemptions: [{ swap_id, status, savings_cents }], new_balance_cents }
```

**Backend implementation:** When a mutation occurs (item added, swap found, claim made, receipt processed), publish to a Redis Pub/Sub channel `list:{listId}`. The SSE endpoint subscribes to this channel and forwards events to connected clients.

### 6.2 Heartbeat

Send a `:keepalive` comment every 30 seconds to prevent proxy/load-balancer timeouts.

---

## 7. Security & Privacy

### 7.1 Authentication & Authorization

| Concern | Implementation |
|---------|---------------|
| **Session management** | HTTP-only, Secure, SameSite=Strict cookie. 7-day rolling expiry. Session ID maps to user in Redis (TTL 7 days). |
| **OTP brute force** | Twilio Verify handles rate limiting. Additionally: max 5 verify attempts per phone per 15 minutes at our API layer. |
| **Family group access** | All list/item/swap endpoints verify `user.id ∈ family_group.members` before returning data. |
| **Brand role gating** | Brand portal endpoints check `user.role = 'brand' AND user.brand_email_verified = true`. |
| **CSRF** | SameSite=Strict cookie + check `Origin` header on mutations. |

### 7.2 Data Privacy

| Data | Classification | Handling |
|------|---------------|----------|
| Phone numbers | PII | Stored encrypted at rest (Postgres column-level encryption or application-level AES-256-GCM). Displayed masked in UI: `***-***-4567`. |
| Receipt images | PII (may contain payment info) | Stored in private S3/R2 bucket. Auto-delete after 90 days. OCR extracts only line items — no card numbers parsed. |
| Shopping list items | Behavioral data | Retained indefinitely for analytics. Anonymizable on account deletion. |
| Wallet balance | Financial | Audit log via `transactions` table. All mutations are append-only. Balance is derived (can be recomputed from transaction history). |

### 7.3 Account Deletion

`DELETE /api/account` — soft-delete the user record, anonymize PII (phone → hash, display_name → "Deleted User"), remove from family groups, delete receipt images from S3. Wallet balance forfeited (or paid out if withdrawal is implemented). 30-day grace period before hard delete.

---

## 8. Observability

### 8.1 Logging

Structured JSON logs via `pino`. All logs include:
- `request_id` (UUID, set via middleware on every request)
- `user_id` (if authenticated)
- `timestamp` (ISO 8601)

Log levels:
- `info`: API requests, job completions, MCP calls
- `warn`: MCP fallbacks triggered, circuit breaker state changes, OCR low-confidence matches
- `error`: Unhandled exceptions, job failures, Groflo redemption rejections

### 8.2 Metrics

Collected via Railway's built-in metrics + custom counters pushed to a lightweight provider (e.g., Axiom or Datadog free tier):

| Metric | Type | Alert Threshold |
|--------|------|----------------|
| `api.request.duration_ms` | Histogram | p95 > 2000ms |
| `ocr.job.duration_ms` | Histogram | p95 > 45000ms |
| `ocr.job.failure_rate` | Rate | > 20% over 1 hour |
| `mcp.kroger.circuit_state` | Gauge | Open for > 5 min |
| `mcp.groflo.circuit_state` | Gauge | Open for > 5 min |
| `swaps.claimed.count` | Counter | — (business metric) |
| `swaps.redeemed.count` | Counter | — (business metric) |
| `receipts.duplicate_blocked` | Counter | > 10/hour (fraud signal) |
| `users.signup.count` | Counter | — (business metric) |
| `referral.payout.total_cents` | Counter | — (business metric) |

### 8.3 Alerting

Slack webhook integration for:
- Any `error`-level log
- Circuit breaker opening on either MCP
- OCR job dead-lettered
- Receipt duplicate rate spike

---

## 9. Performance & Scale Assumptions (V2)

### 9.1 Scale Targets

| Dimension | V2 Target | Notes |
|-----------|-----------|-------|
| Concurrent users | 500 | Early adopters |
| Weekly active users | 2,000 | ~500 families × 4 members |
| List items per week | 20,000 | ~10 items per user per week |
| Receipt uploads per week | 2,000 | ~1 per user per week |
| MCP calls per minute | 50 | Bursty during evening hours |

### 9.2 SLOs

| Endpoint | Target Latency (p95) | Availability |
|----------|---------------------|--------------|
| `POST /api/chat` | < 3000ms (includes LLM call) | 99.5% |
| `GET /api/list/*` | < 300ms | 99.9% |
| `POST /api/swaps/*/claim` | < 500ms | 99.9% |
| `POST /api/receipts/upload` | < 2000ms (upload only, OCR is async) | 99.5% |
| Receipt OCR processing | < 60s end-to-end | 95% (best effort) |

### 9.3 Caching Strategy

| Data | Cache Location | TTL | Invalidation |
|------|---------------|-----|-------------|
| Active shopping list | Redis | 5 min | Invalidate on any list mutation |
| Kroger product search results | Redis | 24 hours | Key: `kroger:search:{hash(query)}` |
| Groflo swap results by category | Redis | 1 hour | Key: `groflo:swaps:{category}` |
| User session | Redis | 7 days (rolling) | Explicit on logout/deletion |

---

## 10. Concurrency & Edge Cases

### 10.1 Concurrent List Edits

Multiple family members may add items simultaneously. Since items are append-only rows in `list_items`, there are no write conflicts. The SSE channel broadcasts `item_added` events so all connected clients see updates in real-time. No optimistic locking needed for V2.

### 10.2 Concurrent Swap Claims

Two family members could try to claim the same swap for the same list item. The `UNIQUE(pop_swap_id, user_id, list_item_id)` constraint

on `claimed_swaps` prevents true duplicates. However, the business question is: can multiple family members each claim the same swap for the same item? The unique constraint as defined allows this (different `user_id`). But only one person shops and buys the item.

**Resolution:** Add a list-item-level lock: `UNIQUE(pop_swap_id, list_item_id)` — only ONE claim per swap per item, regardless of which family member claims it. The UI shows "Claimed by Mom" to other members. If the claimer wants to unclaim, they can release it (update status to `expired`), freeing the slot.

```sql
-- Replace the existing unique constraint with:
ALTER TABLE claimed_swaps
  DROP CONSTRAINT claimed_swaps_pop_swap_id_user_id_list_item_id_key;
ALTER TABLE claimed_swaps
  ADD CONSTRAINT claimed_swaps_one_claim_per_item
  UNIQUE(pop_swap_id, list_item_id)
  WHERE status = 'claimed';
```

This is a **partial unique index** — only enforced for active claims. Expired/rejected claims don't block new ones.

### 10.3 Receipt Submitted Before OCR Completes Previous Receipt

A user could upload two receipts in quick succession. Each OCR job independently loads the user's `claimed` swaps and attempts matching. Race condition: both receipts could match the same claimed swap.

**Resolution:** The `referral-payout` and wallet-credit logic runs inside a Postgres transaction with a `SELECT ... FOR UPDATE` on the `claimed_swap` row. If the swap is already `redeemed` when the second job tries to process it, it skips.

```typescript
await db.transaction(async (tx) => {
  const claim = await tx.query(
    `SELECT * FROM claimed_swaps WHERE id = $1 FOR UPDATE`,
    [claimedSwapId]
  );
  if (claim.status !== 'claimed') {
    // Already redeemed or rejected by another receipt job
    return { skipped: true };
  }
  // Proceed with redemption...
  await tx.query(
    `UPDATE claimed_swaps SET status = 'redeemed', receipt_id = $1, redeemed_at = NOW() WHERE id = $2`,
    [receiptId, claimedSwapId]
  );
  await tx.query(
    `UPDATE users SET wallet_balance_cents = wallet_balance_cents + $1 WHERE id = $2`,
    [savingsCents, userId]
  );
  await tx.query(
    `INSERT INTO transactions (user_id, amount_cents, type, reference_id, description) VALUES ($1, $2, 'swap_redemption', $3, $4)`,
    [userId, savingsCents, claimedSwapId, `PopSwap: ${swapProductName}`]
  );
});
```

### 10.4 User Joins via Both Referral Link and Brand Link

A new user clicks a friend's referral link (`/r/POP-abc`) and also a brand's referral link (`/r/POP-xyz`). Which referrer gets credit?

**Resolution:** First-touch attribution. The `referrer_id` is set on user creation and is immutable. The first link the user visits sets a `ref` cookie (30-day TTL). On OTP verification, if `is_new_user`, read the `ref` cookie and set `referrer_id`. If the cookie contains a brand's ref_code, that brand also gets the "sponsored top slot" benefit.

### 10.5 Brand Is Both Referrer and Swap Provider

A brand refers a user AND that user claims the brand's swap. The brand earns:
1. 30% of revenue from the redemption (as referrer)
2. The swap itself (brand's coupon is used)

This is **intended behavior** — it's the incentive for brands to share their links. No special handling needed; the referral payout job and the swap redemption are independent flows.

### 10.6 Stale List Link Shared After Week Rolls Over

A user shares a list link (`/list/{listId}`) on Monday. By next Monday, the list is archived. Someone clicks the old link.

**Resolution:** The `GET /api/list/:listId` endpoint returns archived lists as read-only (no add/claim actions). The UI shows a banner: "This list is from the week of {date}. [View current list →]".

### 10.7 Kroger MCP Returns Multiple Matches

User says "milk." Kroger returns 47 products. Which one does Pop pick?

**Resolution:** Pop's LLM call includes the Kroger results as context. The system prompt instructs: "Pick the most likely match based on the user's message. If ambiguous (e.g., 'milk' could be whole, 2%, oat), ask the user to clarify." The chat response includes the selected product with image, and the user can correct it.

### 10.8 Groflo Redemption Rejected After Wallet Credit

If we credit the wallet optimistically before Groflo confirms, and Groflo later rejects:

**Resolution:** We do NOT credit optimistically. The flow is strictly:
1. OCR matches line item to claimed swap
2. Call Groflo `create_redemption`
3. Only if Groflo returns `status: "approved"` do we credit the wallet
4. If Groflo is down, the job retries (see §4.2 fallback policy)

The user sees "Processing..." until Groflo confirms.

---

## 11. Frontend Architecture

### 11.1 Page Structure

```
popsavings.com/
├── /                     Landing page + chat widget (unauthenticated)
├── /r/:refCode           Referral landing (sets ref cookie, redirects to /)
├── /f/:shareCode         Family invite (sets family cookie, redirects to /)
├── /list                 Current week's shopping list (authenticated)
├── /list/:listId         Specific list (authenticated, or read-only if archived)
├── /wallet               Wallet balance + transaction history
├── /brands               Brand portal landing
├── /brands/dashboard     Brand dashboard (brand role required)
└── /brands/swaps/new     Create new swap offer
```

### 11.2 Chat Widget

The chat widget is persistent across all authenticated pages (bottom-right floating panel, expandable).

**State management:** React context (`ChatProvider`) wrapping the app layout. Messages stored in local state, synced to server on each send. On page load, hydrate from `GET /api/chat/history` (last 50 messages).

**Typing flow:**
```
User types message
  → Optimistic UI: show user bubble immediately
  → POST /api/chat { message, client_message_id }
  → Show typing indicator
  → On response: render assistant bubble + execute actions
    → If action = item_added: update list state (via SSE or direct refetch)
    → If action = swap_found: show swap card inline in chat
```

### 11.3 Shopping List UI

```
┌─────────────────────────────────────┐
│  🔍 Search to add items...          │
├─────────────────────────────────────┤
│                                     │
│  📦 2% Milk                    [x]  │
│  ┌─ 🏷️ PopSwap: Fairlife 2%  ────┐ │
│  │  Save $2.50 — BOGO             │ │
│  │  [Claim]                       │ │
│  └────────────────────────────────┘ │
│                                     │
│  📦 A1 Steak Sauce              [x] │
│  ┌─ 🏷️ PopSwap: Heinz 57  ──────┐ │
│  │  Save $1.50 — Coupon           │ │
│  │  ⭐ Sponsored                  │ │
│  │  [Claim]                       │ │
│  └────────────────────────────────┘ │
│  ┌─ 🔍 Searching for more swaps...┐ │
│  └────────────────────────────────┘ │
│                                     │
│  📦 Organic Bananas             [x]  │
│  (No swaps available yet)           │
│                                     │
├─────────────────────────────────────┤
│  📸 Upload Receipt                  │
│  👨‍👩‍👧 Share with Family (copy link)  │
│  👫 Share with Friends (copy link)  │
└─────────────────────────────────────┘
```

**Swap ordering within an item:**
1. Sponsored swap (from the brand that referred this user) — always first
2. Highest savings value
3. Most recently added

### 11.4 Receipt Upload Flow

```
User taps "📸 Upload Receipt"
  → Native file picker (camera or gallery)
  → Client-side: compute SHA-256 hash of image bytes
  → POST /api/receipts/upload (multipart)
  → UI shows: "Processing your receipt... ⏳"
  → SSE event: receipt_processed
    → If redemptions found:
      "🎉 We found 3 PopSwaps on your receipt!
       +$2.50 (Fairlife Milk)
       +$1.50 (Heinz 57)
       +$3.00 (Chobani Yogurt)
       New balance: $12.00"
    → If no matches:
      "We processed your receipt but didn't find any
       claimed PopSwaps. Make sure to tap 'Claim'
       before you shop!"
    → If OCR failed:
      "We couldn't read your receipt. Try taking a
       clearer photo in good lighting."
```

---

## 12. Referral & Affiliate System Details

### 12.1 Link Types

| Link | Format | Cookie Set | Duration | Purpose |
|------|--------|-----------|----------|---------|
| Friend referral | `popsavings.com/r/{ref_code}` | `pop_ref={ref_code}` | 30 days | Track who referred the new user |
| Family invite | `popsavings.com/f/{share_code}` | `pop_family={share_code}` | 7 days | Auto-join family group after signup |
| Brand deal share | `popsavings.com/r/{brand_ref_code}?swap={swap_id}` | `pop_ref={brand_ref_code}` | 30 days | Brand shares specific deal; also acts as referral |

### 12.2 Attribution Flow

```
1. User visits /r/POP-abc123
2. Server sets pop_ref cookie = "POP-abc123"
3. User lands on homepage, chats with Pop, enters phone
4. POST /api/auth/verify-otp
5. Backend checks: is_new_user?
   YES:
     - Read pop_ref cookie → look up ref_code → set referrer_id
     - Read pop_family cookie → look up share_code → add to family group
     - Generate user's own ref_code
   NO:
     - Ignore cookies (first-touch only)
6. Return user object with family_group and ref links
```

### 12.3 Revenue Share Calculation

Per the brief: "We get $1 per swap" and "We pay 30% of revenue to the community who signs the users."

```
On each successful redemption:
  groflo_payout_cents = pop_swap.groflo_payout_cents  (e.g., 100 = $1.00)
  
  If user has referrer_id:
    referrer_share = groflo_payout_cents * 0.30  (e.g., 30 cents)
    Credit referrer wallet: +30 cents
    Net revenue: 70 cents
  Else:
    Net revenue: 100 cents
```

### 12.4 Brand Sponsored Slot Logic

When a brand refers a user (brand's `ref_code` is the user's `referrer_id`):
- That brand's swaps appear FIRST in the user's list (marked "⭐ Sponsored")
- This is a permanent benefit for the lifetime of the user (incentivizes brands to drive signups)
- Implementation: when rendering swaps for a list item, query `pop_swaps WHERE brand_id = (SELECT referrer_id FROM users WHERE id = current_user) AND category = item.category`. If found, prepend to swap list.

---

## 13. Database Migrations & Seed Data

### 13.1 Migration Strategy

Using **Prisma Migrate** for schema management. Migrations are version-controlled and run automatically on deploy via Railway's deploy hook:

```bash
# railway.toml (or Procfile)
[deploy]
  startCommand = "npx prisma migrate deploy && npm start"
```

### 13.2 Migration Order

```
001_create_users.sql
002_create_family_groups.sql
003_create_family_group_members.sql
004_create_shopping_lists.sql
005_create_list_items.sql
006_create_pop_swaps.sql
007_create_claimed_swaps.sql
008_create_receipts.sql
009_create_transactions.sql
010_create_brand_outreach_requests.sql
011_create_chat_sessions.sql
012_add_partial_unique_index_claimed_swaps.sql
```

### 13.3 Seed Data (Development)

```typescript
// prisma/seed.ts
- 3 test users (with phone numbers on Twilio test credentials)
- 1 family group with all 3 users
- 1 active shopping list with 5 items
- 3 pop_swaps across different categories
- 1 brand user with verified email
- Referral chain: user1 referred user2, user2 referred user3
```

---

## 14. Environment Configuration

```bash
# .env (Railway environment variables)

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Auth
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_VERIFY_SERVICE_SID=VA...

# AI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# MCP
KROGER_MCP_URL=https://kroger-mcp.example.com/sse
GROFLO_MCP_URL=https://groflo-mcp.example.com/sse

# Storage (receipt images)
S3_BUCKET=pop-receipts
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# App
APP_URL=https://popsavings.com
SESSION_SECRET=<random-64-char>
ENCRYPTION_KEY=<32-byte-hex>  # for PII encryption

# Observability
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

**No secrets in code.** All injected via Railway's environment variable UI.

---

## 15. Rollout Plan

### Phase 1: Foundation (Week 1-2)

**Goal:** User can sign up, chat with Pop, and see a shopping list.

| Task | Details |
|------|---------|
| Project scaffold | Next.js 14 app router, Prisma, Railway deploy pipeline |
| Database schema | Migrations 001-011 |
| Auth flow | Twilio Verify OTP, session cookie, middleware |
| Chat backend | `/api/chat` with GPT-4o, system prompt, tool calling stub |
| Chat frontend | Floating widget, message bubbles, typing indicator |
| List backend | CRUD APIs for list items |
| List frontend | Basic list view with search bar |
| Referral links | `ref_code` generation, cookie-based attribution, copylink UI |
| Family sharing | Share code generation, `/f/:shareCode` join flow |

**Exit criteria:** A user can text their phone, get an OTP, chat with Pop, add "milk" to a list, and share the list link with a family member

who can also sign up and see the same list.

### Phase 2: Product Enrichment (Week 3)

| Task | Details |
|------|---------|
| Kroger MCP client | MCP TypeScript SDK integration, circuit breaker wrapper |
| Product enrichment flow | On item add → search Kroger → store product_id, image, category |
| Enriched list UI | Product images, category grouping, brand names |
| Fallback handling | If Kroger unavailable, show raw text; enqueue retry job |
| Search UI | `/api/list/:listId/items/search` → Kroger results → user picks → add to list |

**Exit criteria:** When a user adds "yogurt," the list shows a product image, brand name, and category from Kroger.

### Phase 3: PopSwaps (Week 4-5)

| Task | Details |
|------|---------|
| Groflo MCP client | MCP TypeScript SDK integration, circuit breaker wrapper |
| Swap search flow | On item add → search Groflo by category/name → insert pop_swaps |
| Swap UI | Swap cards under each list item with savings amount and offer type |
| Claim flow | `/api/swaps/:swapId/claim` endpoint, UI button, "Claimed by X" state |
| SSE infrastructure | Redis Pub/Sub → SSE endpoint → real-time swap and claim updates |
| Swap search background job | BullMQ retry job for when Groflo is unavailable |

**Exit criteria:** User adds "A1 Sauce," sees a PopSwap for "Heinz 57 — Save $2.50," taps Claim, and other family members see it as claimed.

### Phase 4: Receipt Redemption (Week 6-7)

| Task | Details |
|------|---------|
| S3/R2 setup | Private bucket, upload presigned URL or direct multipart |
| Receipt upload API | `/api/receipts/upload` with hash dedup, file validation |
| OCR worker | BullMQ job, GPT-4o Vision, structured line item extraction |
| Fuzzy matching engine | Normalize receipt text, Levenshtein matching against claimed swaps |
| Groflo redemption call | `create_redemption` via MCP, handle approve/reject |
| Wallet credit | Transaction insert, balance update within Postgres transaction |
| Wallet UI | `/wallet` page showing balance and transaction history |
| Receipt status UI | SSE-driven status updates, success/failure messaging |
| Duplicate receipt detection | SHA-256 hash unique index, user-facing error |

**Exit criteria:** User claims a swap, shops, uploads receipt photo, and sees wallet credited with the savings amount within 60 seconds.

### Phase 5: Brand Portal (Week 8-9)

| Task | Details |
|------|---------|
| Brand email verification | OTP-style code sent to corporate email, confirm endpoint |
| Brand dashboard | Active swaps, claim/redemption counts, demand signals |
| Create swap UI | Form to propose a PopSwap with product details and Groflo coupon ID |
| Brand outreach job | Semi-automated: Slack notification to ops with category + demand count |
| Brand referral tracking | Brand ref_code, sponsored slot logic, revenue share stats |
| Brand copylink UI | Share deal link that doubles as referral link |

**Exit criteria:** A brand PM receives an outreach email, signs up at popsavings.com/brands, verifies their corporate email, creates a PopSwap offer, and sees it appear on users' lists. Brand can also share a deal link that drives signups attributed to them.

### Phase 6: Polish & Launch Prep (Week 10)

| Task | Details |
|------|---------|
| Error handling audit | Every API endpoint returns proper error codes per §3.9 |
| Rate limiting | Express-rate-limit on auth endpoints, chat endpoint (20 req/min/user) |
| Logging & alerting | Pino structured logging, Slack alerts for errors and circuit breakers |
| Load testing | Simulate 500 concurrent users with k6; verify SLOs from §9.2 |
| Security review | OWASP top 10 check, PII encryption verification, session hardening |
| Landing page | Marketing copy, "How it works" flow, CTA to chat with Pop |
| Analytics | Track signup, first item added, first claim, first redemption (funnel) |
| Mobile responsiveness | Test chat widget + list UI on iOS Safari, Android Chrome |

**Exit criteria:** System handles 500 concurrent users within SLO targets. All error paths are handled gracefully. Landing page converts visitors to signups.

---

## 16. Testing Strategy

### 16.1 Unit Tests

| Layer | Tool | Coverage Target | Focus Areas |
|-------|------|----------------|-------------|
| API route handlers | Vitest | 80% | Input validation, auth checks, error responses |
| Fuzzy matching engine | Vitest | 95% | Receipt text normalization, Levenshtein threshold edge cases |
| Referral calculation | Vitest | 95% | 30% math, edge cases (no referrer, brand referrer, rounding) |
| Wallet mutations | Vitest | 95% | Cents arithmetic, concurrent credit prevention |

### 16.2 Integration Tests

| Scenario | Approach |
|----------|----------|
| OTP flow | Mock Twilio Verify; test full signup → session → authenticated request |
| Chat → Item → Swap | Mock OpenAI + Kroger MCP + Groflo MCP; verify DB state after chat message |
| Receipt → Redemption → Wallet | Mock GPT-4o Vision + Groflo MCP; verify claimed_swap status transition and wallet balance |
| Referral attribution | Create referrer, simulate new user signup with ref cookie, verify referrer_id set |
| Duplicate receipt | Upload same image twice; verify 409 on second attempt |

### 16.3 End-to-End Tests

Playwright tests against a staging environment:

```
1. Visit popsavings.com
2. Chat with Pop, enter phone, verify OTP (test number)
3. Say "I need milk and eggs"
4. Verify list shows 2 items with images
5. Click Claim on a swap
6. Upload a test receipt image
7. Verify wallet shows credit
8. Copy family share link
9. Open in incognito, sign up as family member
10. Verify same list is visible
```

---

## 17. Cost Estimates (V2 at 2,000 WAU)

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Railway (API + Worker) | $20-40 | 2 services, ~512MB RAM each |
| Railway PostgreSQL | $10-20 | Starter plan, <1GB data |
| Railway Redis | $10 | Starter plan |
| Twilio Verify | $100 | ~2,000 verifications × $0.05 |
| OpenAI GPT-4o | $200-400 | Chat: ~10 msgs/user/week × 2K users × $0.01/msg. OCR: ~2K receipts × $0.05/receipt |
| S3/R2 (receipts) | $5 | <10GB storage, Cloudflare R2 is cheaper |
| Domain + DNS | $15/year | popsavings.com |
| **Total** | **~$350-600/mo** | |

**Revenue at 2,000 WAU:** If 50% of users redeem 1 swap/week = 1,000 redemptions × $1.00 = **$4,000/mo revenue**. Comfortable margin even at V2 scale.

---

## 18. Open Technical Decisions (Requiring Input)

These are decisions that can be deferred to implementation time but should be consciously made:

| # | Decision | Options | Recommendation | Impact if Wrong |
|---|----------|---------|---------------|----------------|
| 1 | **Kroger MCP: build or consume?** | (a) Connect to existing MCP server (b) Build MCP server wrapping Kroger API | (b) Build it — gives us control over caching and schema | 1-2 days extra work |
| 2 | **Groflo MCP: redemption flow** | (a) We OCR + call Groflo to confirm (b) We send receipt image to Groflo, they OCR | (a) We own OCR — more control, faster iteration | If Groflo expects (b), integration rework |
| 3 | **Receipt storage** | (a) AWS S3 (b) Cloudflare R2 (c) Railway volume | (b) R2 — zero egress fees, S3-compatible API | Minimal — easy to swap |
| 4 | **Chat history persistence** | (a) JSONB in chat_sessions (b) Separate chat_messages table | (a) for V2 — simpler. Migrate to (b) if >50 msgs/session becomes common | Query performance at scale |
| 5 | **Wallet withdrawal rail** | (a) Stripe Connect (b) PayPal (c) Venmo (d) Defer to V3 | (d) Defer — V2 wallet is display-only. Implement withdrawal when balance accumulation proves the model | Users may want to cash out sooner |

---

## 19. Glossary

| Term | Definition |
|------|-----------|
| **Pop** | The AI agent (consumer-facing name, V2). Previously "Bob." |
| **PopSwap™** | A brand-sponsored product swap offer (e.g., "Buy Heinz 57 instead of A1, save $2.50"). |
| **MCP** | Model Context Protocol — an open standard for connecting AI models to external tools/data sources. |
| **Kroger MCP** | MCP server providing grocery product data (name, image, price, category, UPC). |
| **Groflo MCP** | MCP server providing digital coupon data and redemption confirmation. |
| **Jeremy / Wattdata** | Third-party contact-sourcing tools used to find CPG brand product managers for outreach. |
| **Ref Code** | A unique alphanumeric code assigned to each user (e.g., `POP-a3x9k2`) used in referral/affiliate links. |
| **Share Code** | A unique code for each family group (e.g., `FAM-x7y2z`) used in family invite links. |
| **Sponsored Slot** | The top swap position in a user's list, reserved for the brand that referred that user. |
| **Wallet** | An in-app balance (stored in cents) credited when users redeem PopSwaps. Withdrawal deferred to V3. |
| **Circuit Breaker** | A fault-tolerance pattern that stops calling a failing external service and returns a fallback instead. |