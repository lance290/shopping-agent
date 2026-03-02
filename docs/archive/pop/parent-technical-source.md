# Technical Specification: Bob — AI Family Shopping Agent

**Version:** 0.1 (Draft)
**Author:** Engineering
**Status:** RFC — Pending answers to open questions
**Last Updated:** 2025-01-XX

---

## 1. System Overview

Bob is a multi-channel AI agent that participates in family communication threads (SMS, Email, WhatsApp) to build shared grocery lists, surface brand-sponsored swaps/coupons via Groflo's MCP, and process receipt-based redemptions into a user wallet.

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INBOUND CHANNELS                      │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐              │
│  │ Twilio   │  │ Mailgun  │  │ WhatsApp  │              │
│  │ SMS/MMS  │  │ Inbound  │  │ Business  │              │
│  │ Webhook  │  │ Parse    │  │ API       │              │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘              │
│       │              │              │                    │
│       └──────────────┼──────────────┘                    │
│                      ▼                                   │
│         ┌────────────────────────┐                       │
│         │  Message Normalizer    │                       │
│         │  (Channel Adapter)     │                       │
│         └───────────┬────────────┘                       │
│                     ▼                                    │
│         ┌────────────────────────┐                       │
│         │  Bob Core Engine       │                       │
│         │  ┌──────────────────┐  │                       │
│         │  │ NLU / Intent     │  │                       │
│         │  │ (GPT-4o)         │  │                       │
│         │  └──────────────────┘  │                       │
│         │  ┌──────────────────┐  │                       │
│         │  │ Conversation     │  │                       │
│         │  │ State Machine    │  │                       │
│         │  └──────────────────┘  │                       │
│         │  ┌──────────────────┐  │                       │
│         │  │ List Manager     │  │                       │
│         │  └──────────────────┘  │                       │
│         └───────────┬────────────┘                       │
│                     │                                    │
│        ┌────────────┼────────────────┐                   │
│        ▼            ▼                ▼                   │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ Groflo   │ │ Brand Bid    │ │ Receipt      │         │
│  │ MCP      │ │ Engine       │ │ Processor    │         │
│  │ Client   │ │              │ │ (BullMQ)     │         │
│  └──────────┘ └──────────────┘ └──────────────┘         │
│                                                          │
│         ┌────────────────────────┐                       │
│         │  Web App (Next.js)     │                       │
│         │  - Shopping List View  │                       │
│         │  - Brand Portal        │                       │
│         │  - Wallet Dashboard    │                       │
│         └────────────────────────┘                       │
│                                                          │
│         ┌────────────────────────┐                       │
│         │  PostgreSQL + Redis    │                       │
│         └────────────────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Channel Adapters

### 2.1 SMS/MMS (Twilio)

**Setup:**
- Provision a Twilio phone number (initially one; scale to number pool if needed).
- Configure webhook for inbound SMS/MMS at `POST /api/webhooks/twilio`.
- Twilio Messaging Service for outbound with sticky sender.

**Group MMS Behavior:**
- When Bob's Twilio number is added to an iMessage group, Apple downgrades the thread to Group MMS.
- Twilio receives group MMS via `MessagingServiceSid` with participant phone numbers in the `From` field and `NumMedia` for images.
- **Limitation:** Twilio cannot reliably distinguish between multiple group MMS threads involving the same participants. We mitigate by tracking `MessageSid` chains and using our own `FamilyGroupID` mapping.

**Decision Point (DP-1):** If Group MMS proves unreliable in testing, fallback to 1:1 SMS where Bob aggregates messages to the shared web list and sends list-link updates to all family members individually.

**Webhook Payload Processing:**
```typescript
interface TwilioInbound {
  MessageSid: string;
  From: string;        // E.164 phone number
  To: string;          // Bob's Twilio number
  Body: string;
  NumMedia: string;
  MediaUrl0?: string;  // Receipt image
  // Group MMS fields
  AddressCount?: string;
  AddressSid?: string;
}
```

### 2.2 Email (Mailgun)

**Setup:**
- Domain: `buy-anything.com`
- Primary address: `bob@buy-anything.com`
- Dynamic aliases: `list-{familyGroupId}@buy-anything.com` (for thread isolation per family)
- Mailgun Inbound Parse → `POST /api/webhooks/mailgun`

**Threading Strategy:**
- On first contact, Bob replies with a `References` / `In-Reply-To` header chain.
- For group emails, Bob is CC'd. We parse `To`, `CC`, and `From` to identify all participants.
- Bob generates a per-family alias and asks users to use it for list-related emails (reducing noise from unrelated threads).

**Payload Processing:**
```typescript
interface MailgunInbound {
  sender: string;
  from: string;
  subject: string;
  'body-plain': string;
  'body-html': string;
  recipient: string;
  'Message-Id': string;
  'In-Reply-To'?: string;
  References?: string;
  // Attachments for receipts
  'attachment-count'?: string;
  'attachment-1'?: File;
}
```

### 2.3 WhatsApp (Meta Business API)

**Setup:**
- WhatsApp Business Account via Meta Cloud API.
- Webhook at `POST /api/webhooks/whatsapp`.
- **Constraint:** WABA cannot join user-created groups. Bob operates in 1:1 mode; all messages sync to the shared web list.

**MVP Approach:** WhatsApp is Phase 4 (V4). For MVP, SMS + Email only.

### 2.4 Normalized Message Schema

All adapters produce a canonical `InboundMessage`:

```typescript
interface InboundMessage {
  id: string;                    // UUID, generated
  channel: 'sms' | 'email' | 'whatsapp';
  channelMessageId: string;      // Provider's message ID
  senderIdentifier: string;      // Phone (E.164) or email
  recipientIdentifier: string;   // Bob's number or email
  groupParticipants?: string[];  // Other participants if group
  body: string;                  // Plain text content
  mediaUrls?: string[];          // Attached images (receipts)
  receivedAt: Date;
  rawPayload: Record<string, any>; // Full provider payload
}
```

---

## 3. Data Model (PostgreSQL)

### 3.1 Entity Relationship Diagram

```
User 1──N UserFamilyGroup N──1 FamilyGroup
                                    │
                                    1
                                    │
                                    N
                              ShoppingList
                                    │
                                    1
                                    │
                                    N
                               ListItem ──N── ListItemSwap ──1── Swap
                                                                   │
                                                                   N
                                                                   │
                                                                 Brand
                                    │
                               Claim ──1── Receipt
                                    │
                              Transaction
                                    │
                                  User (wallet)

ReferralLink ── User (referrer)
             ── User (referred)
```

### 3.2 Table Definitions

```sql
-- Users (both consumers and brand users)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone VARCHAR(20) UNIQUE,          -- E.164, nullable
  email VARCHAR(255) UNIQUE,         -- nullable
  phone_verified BOOLEAN DEFAULT FALSE,
  email_verified BOOLEAN DEFAULT FALSE,
  wallet_balance_cents INTEGER DEFAULT 0,  -- ledger-backed, see Transactions
  user_type VARCHAR(20) NOT NULL DEFAULT 'consumer', -- 'consumer' | 'brand_admin'
  referred_by_user_id UUID REFERENCES users(id),
  referral_code VARCHAR(20) UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_phone ON users(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_referral_code ON users(referral_code);

-- Family Groups
CREATE TABLE family_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100),
  created_by UUID NOT NULL REFERENCES users(id),
  email_alias VARCHAR(100) UNIQUE,   -- e.g., 'list-abc123'
  channel_metadata JSONB DEFAULT '{}', -- stores group MMS thread IDs, etc.
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User <-> FamilyGroup (many-to-many)
CREATE TABLE user_family_groups (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  family_group_id UUID REFERENCES family_groups(id) ON DELETE CASCADE,
  role VARCHAR(20) DEFAULT 'member',  -- 'owner' | 'member'
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, family_group_id)
);

-- Shopping Lists (one active per family at a time, historical preserved)
CREATE TABLE shopping_lists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_group_id UUID NOT NULL REFERENCES family_groups(id),
  status VARCHAR(20) DEFAULT 'active

', -- 'active' | 'completed' | 'archived'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX idx_shopping_lists_family_active ON shopping_lists(family_group_id, status) WHERE status = 'active';

-- List Items
CREATE TABLE list_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shopping_list_id UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
  added_by UUID NOT NULL REFERENCES users(id),
  raw_text VARCHAR(500) NOT NULL,           -- "get some 2% milk"
  normalized_name VARCHAR(255),             -- "2% Milk"
  category VARCHAR(100),                    -- "Dairy"
  groflo_product_id VARCHAR(100),           -- from Groflo MCP item lookup
  quantity INTEGER DEFAULT 1,
  status VARCHAR(20) DEFAULT 'pending',     -- 'pending' | 'claimed' | 'bought' | 'removed'
  source_channel VARCHAR(20),               -- 'sms' | 'email' | 'whatsapp' | 'web'
  source_message_id VARCHAR(255),           -- reference to InboundMessage
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_list_items_list ON list_items(shopping_list_id);
CREATE INDEX idx_list_items_category ON list_items(category);

-- Brands
CREATE TABLE brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  brand_email VARCHAR(255) UNIQUE,
  brand_email_verified BOOLEAN DEFAULT FALSE,
  admin_user_id UUID REFERENCES users(id),  -- brand admin who registered
  category VARCHAR(100),                     -- primary product category
  referral_code VARCHAR(20) UNIQUE,
  logo_url VARCHAR(500),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Swaps (coupon/deal offers from brands or Groflo)
CREATE TABLE swaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id),
  groflo_coupon_id VARCHAR(100),            -- NULL if brand-direct, populated if from Groflo MCP
  swap_type VARCHAR(20) NOT NULL,           -- 'coupon' | 'bogo' | 'discount_cents' | 'discount_pct'
  description VARCHAR(500) NOT NULL,        -- "Buy Fairlife Milk, save $2.00"
  discount_value_cents INTEGER NOT NULL,    -- normalized to cents
  target_category VARCHAR(100),             -- "Dairy"
  target_product_keywords VARCHAR(255)[],   -- ["milk", "2%", "whole"]
  min_purchase_qty INTEGER DEFAULT 1,
  max_claims_total INTEGER,                 -- NULL = unlimited
  max_claims_per_user INTEGER DEFAULT 1,
  current_claims_count INTEGER DEFAULT 0,
  bid_amount_cents INTEGER DEFAULT 0,       -- what brand pays Groflo per redemption
  is_autobid BOOLEAN DEFAULT FALSE,         -- brand's standing offer
  status VARCHAR(20) DEFAULT 'active',      -- 'active' | 'paused' | 'expired' | 'exhausted'
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_swaps_category ON swaps(target_category, status) WHERE status = 'active';
CREATE INDEX idx_swaps_groflo ON swaps(groflo_coupon_id) WHERE groflo_coupon_id IS NOT NULL;

-- ListItem <-> Swap association (which swaps are shown under which items)
CREATE TABLE list_item_swaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  list_item_id UUID NOT NULL REFERENCES list_items(id) ON DELETE CASCADE,
  swap_id UUID NOT NULL REFERENCES swaps(id),
  rank INTEGER DEFAULT 0,                   -- display order (sponsored = 0)
  is_sponsored BOOLEAN DEFAULT FALSE,       -- brand-affiliated top spot
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(list_item_id, swap_id)
);

-- Claims (user commits to buying a swap)
CREATE TABLE claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  swap_id UUID NOT NULL REFERENCES swaps(id),
  list_item_id UUID NOT NULL REFERENCES list_items(id),
  shopping_list_id UUID NOT NULL REFERENCES shopping_lists(id),
  status VARCHAR(20) DEFAULT 'claimed',     -- 'claimed' | 'redeemed' | 'expired' | 'cancelled'
  claimed_at TIMESTAMPTZ DEFAULT NOW(),
  redeemed_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,          -- claim window (e.g., 7 days)
  receipt_id UUID REFERENCES receipts(id)
);
CREATE INDEX idx_claims_user_status ON claims(user_id, status);
CREATE INDEX idx_claims_swap ON claims(swap_id);
CREATE UNIQUE INDEX idx_claims_user_swap_list ON claims(user_id, swap_id, shopping_list_id) WHERE status != 'cancelled';

-- Receipts
CREATE TABLE receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  image_url VARCHAR(500) NOT NULL,          -- S3/R2 URL
  source_channel VARCHAR(20),               -- how it was submitted
  ocr_status VARCHAR(20) DEFAULT 'pending', -- 'pending' | 'processing' | 'completed' | 'failed'
  ocr_result JSONB,                         -- structured OCR output
  store_name VARCHAR(255),
  receipt_date DATE,
  receipt_total_cents INTEGER,
  fingerprint VARCHAR(255),                 -- dedup hash (store+date+total+last4items)
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_receipts_fingerprint ON receipts(fingerprint) WHERE fingerprint IS NOT NULL;
CREATE INDEX idx_receipts_user ON receipts(user_id);

-- Transactions (append-only ledger for wallet)
CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  type VARCHAR(30) NOT NULL,                -- 'redemption_credit' | 'referral_credit' | 'payout' | 'adjustment'
  amount_cents INTEGER NOT NULL,            -- positive = credit, negative = debit
  balance_after_cents INTEGER NOT NULL,     -- running balance snapshot
  reference_type VARCHAR(30),               -- 'claim' | 'referral' | 'payout_request'
  reference_id UUID,                        -- FK to claims.id, users.id, etc.
  description VARCHAR(500),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_transactions_user ON transactions(user_id, created_at DESC);

-- Referral Links
CREATE TABLE referral_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id UUID NOT NULL REFERENCES users(id),
  referrer_type VARCHAR(20) NOT NULL,       -- 'consumer' | 'brand'
  code VARCHAR(20) NOT NULL UNIQUE,         -- short code in URL
  brand_id UUID REFERENCES brands(id),      -- if brand referral
  click_count INTEGER DEFAULT 0,
  signup_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation State (for Bob's stateful chat logic)
CREATE TABLE conversation_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  channel VARCHAR(20) NOT NULL,
  state VARCHAR(50) NOT NULL,               -- 'onboarding' | 'awaiting_family' | 'active' | 'receipt_pending'
  context JSONB DEFAULT '{}',               -- arbitrary state data
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, channel)
);
```

### 3.3 Redis Key Patterns

```
# Active list cache (hot path for web view)
list:{shoppingListId}              → JSON of full list with items + swaps (TTL: 5min, invalidate on write)

# Conversation state (fast lookup for message processing)
conv:{channel}:{senderIdentifier}  → JSON of conversation_states row (TTL: 24h, write-through)

# Rate limiting
ratelimit:sms:{phone}             → counter (TTL: 60s, max 10 messages/min)
ratelimit:email:{email}           → counter (TTL: 60s, max 20 messages/min)

# Brand bid request dedup
bidreq:{category}:{dateKey}       → SET of brandIds already notified today
```

---

## 4. API Design

### 4.1 Webhook Endpoints (Inbound — Server-to-Server)

All webhook endpoints validate provider signatures before processing.

```
POST /api/webhooks/twilio
  - Validates X-Twilio-Signature
  - Produces InboundMessage → publishes to BullMQ "messages" queue
  - Returns 200 (empty TwiML) immediately

POST /api/webhooks/mailgun
  - Validates Mailgun signature (timestamp + token + signing key)
  - Produces InboundMessage → publishes to BullMQ "messages" queue
  - Returns 200 immediately

POST /api/webhooks/whatsapp  (V4)
  - Validates Meta webhook signature
  - Same flow as above
```

### 4.2 Web App API (Next.js API Routes — User-Facing)

**Authentication:** Passwordless. Users receive a magic link or OTP via SMS/email. Session managed via HTTP-only cookie with JWT (7-day expiry). Web list links contain a signed token for unauthenticated "view-only" access; "Claim" requires auth.

```
# --- Shopping List ---
GET    /api/lists/:listId
  → { list: ShoppingList, items: ListItemWithSwaps[], familyMembers: User[] }
  Auth: signed link token (read-only) OR session cookie (full access)

POST   /api/lists/:listId/items
  Body: { text: string }
  → { item: ListItem, matchedSwaps: Swap[] }
  Auth: session cookie

PATCH  /api/lists/:listId/items/:itemId
  Body: { status?: string, quantity?: number }
  Auth: session cookie

GET    /api/lists/:listId/items/search?q=yogurt
  → { results: GrofloProduct[] }   // proxied MCP call
  Auth: session cookie

# --- Claims ---
POST   /api/claims
  Body: { swapId: string, listItemId: string, shoppingListId: string }
  → { claim: Claim }
  Auth: session cookie
  Idempotency: unique constraint on (user, swap, list) prevents double-claim

DELETE /api/claims/:claimId
  → { claim: Claim }  // status → 'cancelled'
  Auth: session cookie, must own claim

# --- Receipts ---
POST   /api/receipts
  Body: multipart/form-data { image: File }
  → { receipt: { id, status: 'pending' } }
  Auth: session cookie
  Side effect: enqueues OCR job

GET    /api/receipts/:receiptId
  → { receipt: Receipt, matchedClaims: Claim[] }
  Auth: session cookie

# --- Wallet ---
GET    /api/wallet
  → { balance_cents: number, transactions: Transaction[] }
  Auth: session cookie

POST   /api/wallet/payout
  Body: { amount_cents: number, method: 'stripe' | 'venmo' }
  → { transaction: Transaction }
  Auth: session cookie
  Constraint: minimum payout $5.00 (DP-2: confirm threshold)

# --- Auth ---
POST   /api/auth/otp/request
  Body: { phone?: string, email?: string }
  → { sent: true }

POST   /api/auth/otp/verify
  Body: { phone?: string, email?: string, code: string }
  → { token: string }  // sets HTTP-only cookie

# --- Brand Portal ---
POST   /api/brands/register
  Body: { brandName, brandEmail, category }
  Auth: session cookie (must be verified user)
  → { brand: Brand }

POST   /api/brands/:brandId/swaps
  Body: { swapType, description, discountValueCents, targetCategory, targetProductKeywords[], expiresAt, bidAmountCents, isAutobid }
  Auth: session cookie, must be brand admin
  → { swap: Swap }

GET    /api/brands/:brandId/dashboard
  → { activeSwaps: Swap[], totalRedemptions, totalSpendCents, affiliateSignups }
  Auth: session cookie, must be brand admin

# --- Referrals ---
GET    /api/referral/link
  → { url: string, code: string }
  Auth: session cookie

GET    /api/referral/stats
  → { clickCount, signupCount, earningsCents }
  Auth: session cookie
```

### 4.3 Groflo MCP Client

Based on the MCP (Model Context Protocol) standard, we implement a client that calls Groflo's MCP server. **Assumed tool interface** (DP-3: must confirm with Groflo):

```typescript
// Tool: groflo_item_lookup
// Normalizes free-text grocery item to structured product
interface GrofloItemLookupInput {
  query: string;        // "2% milk"
  locale?: string;      // "en-US"
}
interface GrofloItemLookupOutput {
  products: {
    groflo_product_id: string;
    name: string;
    category: string;
    brand: string;
    upc?: string;
  }[];
}

// Tool: groflo_swap_search
// Finds available coupons/swaps for a product or category
interface GrofloSwapSearchInput {
  product_id?: string;
  category?: string;
  zip_code?: string;
}
interface GrofloSwapSearchOutput {
  swaps: {
    groflo_coupon_id: string;
    brand_name: string;
    swap_type: 'coupon' | 'bogo' | 'discount';
    description: string;
    discount_value_cents: number;
    expires_at: string;
  }[];
}

// Tool: groflo_redeem
// Marks a coupon as redeemed after receipt validation
interface GrofloRedeemInput {
  groflo_coupon_id: string;
  receipt_data: {
    store_name: string;
    receipt_date: string;
    line_items: { description: string; price_cents: number }[];
    total_cents: number;
  };
  user_id: string;
}
interface GrofloRedeemOutput {
  success: boolean;
  redemption_id: string;
  credit_amount_cents: number;
  error?: string;
}
```

**MCP Transport:** Assumed SSE (Server-Sent Events) per MCP spec. If Groflo exposes HTTP REST instead, we wrap it in the same interface.

---

## 5. Background Jobs (BullMQ)

### 5.1 Queue: `messages`

**Purpose:** Process all inbound messages from all channels.

```typescript
// Job payload
interface MessageJob {
  message: InboundMessage;
}

// Processing pipeline:
// 1. Resolve sender → User (create if new, via phone/email lookup)
// 2. Load conversation state
// 3. Route based on state:
//    - 'new': Start onboarding flow
//    - 'onboarding

': Continue collecting family member info
//    - 'active': Process as potential list item or command
//    - 'receipt_pending': Check for image attachment
// 4. If state is 'active':
//    a. Send body to NLU for intent classification
//    b. If intent = 'add_item': extract item → call Groflo item lookup → create ListItem → fetch swaps → respond with list link
//    c. If intent = 'chat': ignore (no response)
//    d. If intent = 'command': handle ("done shopping", "show list", "help", etc.)
//    e. If image attached: route to receipt processing
// 5. Update conversation state
// 6. Send outbound response via appropriate channel adapter

// Concurrency: 10 workers
// Retry: 3 attempts, exponential backoff (1s, 5s, 25s)
// Timeout: 30s per job
// Dead letter queue: 'messages-dlq'
```

### 5.2 Queue: `receipt-processing`

**Purpose:** Async OCR and redemption validation for receipt images.

```typescript
interface ReceiptJob {
  receiptId: string;
  userId: string;
  imageUrl: string;
}

// Processing pipeline:
// 1. Update receipt status → 'processing'
// 2. Call GPT-4o Vision API with receipt image
//    Prompt: Extract store name, date, line items (description + price), total
// 3. Parse structured response into ReceiptOCRResult
// 4. Generate fingerprint: SHA256(storeName + date + totalCents + sortedFirst4Items)
// 5. Check fingerprint uniqueness against receipts table
//    - If duplicate: mark receipt as 'failed', reason: 'duplicate_receipt'
//    - Return early
// 6. Store OCR result in receipt record
// 7. Load all 'claimed' claims for this user with non-expired claim windows
// 8. For each claim, attempt to match against receipt line items:
//    a. Fuzzy match claim's swap target_product_keywords against receipt line item descriptions
//    b. Confidence threshold: 0.75 (DP-4: tune based on testing)
//    c. If match found:
//       - If swap has groflo_coupon_id: call groflo_redeem MCP tool
//       - If brand-direct swap: mark as redeemed internally
//       - Update claim status → 'redeemed'
//       - Credit user wallet (see Transaction creation below)
//       - Credit referrer wallet if applicable (30% of revenue)
//       - Decrement swap.current_claims_count
// 9. Update receipt status → 'completed'
// 10. Send summary message to user via their preferred channel:
//     "Receipt processed! 2 swaps redeemed. $4.50 added to your Bob Wallet."

// Concurrency: 5 workers (rate-limited by OpenAI API)
// Retry: 2 attempts, backoff (5s, 30s)
// Timeout: 60s per job
// Dead letter queue: 'receipts-dlq'
```

### 5.3 Queue: `brand-outreach`

**Purpose:** Notify brands when demand exists in their category and no active swaps are available.

```typescript
interface BrandOutreachJob {
  category: string;
  demandCount: number;        // how many users want items in this category
  familyGroupCount: number;   // how many families
  triggeredByListItemId: string;
}

// Processing pipeline:
// 1. Check Redis bidreq:{category}:{dateKey} — skip if brands already notified today
// 2. Find all brands with matching category that have brand_email_verified = true
// 3. For each brand:
//    a. Send email via Mailgun:
//       Subject: "{demandCount} shoppers are looking for {category} deals this week"
//       Body: Anonymized demand data + CTA link to brand portal to create a swap
//    b. Add brandId to Redis SET
// 4. Log outreach event for analytics

// Concurrency: 3 workers
// Retry: 1 attempt
// Timeout: 15s
// Schedule: Also runs as cron job every Monday 9am ET to batch weekly demand
```

### 5.4 Queue: `list-swap-matching`

**Purpose:** When a new ListItem is created, find and attach relevant swaps.

```typescript
interface SwapMatchJob {
  listItemId: string;
  shoppingListId: string;
  normalizedName: string;
  category: string;
  grofloProductId?: string;
}

// Processing pipeline:
// 1. Query Groflo MCP (groflo_swap_search) by product_id and category
// 2. Query local swaps table for active brand-direct swaps matching category + keywords
// 3. Merge and deduplicate results
// 4. Rank swaps:
//    a. Sponsored swaps from brands whose referral code signed up this family → rank 0, is_sponsored = true
//    b. Highest discount value → rank 1, 2, 3...
//    c. Max 5 swaps per item
// 5. Insert into list_item_swaps
// 6. Invalidate Redis list cache: list:{shoppingListId}
// 7. If no swaps found and category has registered brands:
//    Enqueue brand-outreach job

// Concurrency: 10 workers
// Retry: 2 attempts
// Timeout: 15s
```

### 5.5 Scheduled Jobs (Cron via BullMQ Repeatable)

```typescript
// Weekly list reset prompt — Sundays 8pm user's timezone (default ET)
// Sends message: "Starting a fresh list for the week! Text me what you need."
{
  name: 'weekly-list-prompt',
  pattern: '0 20 * * 0',  // Sunday 8pm
  handler: async () => {
    // 1. Find all active family groups
    // 2. Create new shopping_list, set previous to 'archived'
    // 3. Send list link to all family members via their preferred channel
  }
}

// Claim expiry — runs hourly
{
  name: 'expire-claims',
  pattern: '0 * * * *',
  handler: async () => {
    // UPDATE claims SET status = 'expired' WHERE status = 'claimed' AND expires_at < NOW()
  }
}

// Swap expiry — runs hourly
{
  name: 'expire-swaps',
  pattern: '0 * * * *',
  handler: async () => {
    // UPDATE swaps SET status = 'expired' WHERE status = 'active' AND expires_at < NOW()
  }
}

// Weekly brand demand digest — Mondays 9am ET
{
  name: 'brand-demand-digest',
  pattern: '0 9 * * 1',
  handler: async () => {
    // Aggregate list_items by category from past 7 days
    // Enqueue brand-outreach jobs for categories with demand > threshold (e.g., 10+ items)
  }
}
```

---

## 6. NLU / Intent Classification

### 6.1 Intent Model

Using GPT-4o with structured output (JSON mode) for intent classification:

```typescript
interface NLURequest {
  message: string;
  conversationHistory: { role: string; content: string }[];  // last 5 messages
  currentListItems: string[];  // for context
}

interface NLUResponse {
  intent: 'add_item' | 'remove_item' | 'show_list' | 'done_shopping' | 'help' | 'chat' | 'unknown';
  items?: {
    raw: string;
    normalized: string;
    quantity: number;
    category?: string;
  }[];
  confidence: number;
}
```

**System Prompt:**
```
You are a grocery list assistant parser. Given a message from a family group chat, determine if the sender is requesting to add grocery items to a shopping list or just chatting.

Rules:
- "we need milk" → add_item
- "can you grab eggs" → add_item  
- "I love that new yogurt" → chat (expressing opinion, not requesting purchase)
- "milk, eggs, bread" → add_item (multiple items)
- "what's on the list" → show_list
- "I'm done shopping" → done_shopping
- "remove the milk" → remove_item

Return JSON with intent and extracted items if applicable.
```

### 6.2 Cost & Latency Budget

- **Target latency:** < 2s for intent classification (acceptable for async messaging)
- **Estimated cost:** ~$0.002 per message (GPT-4o input ~200 tokens, output ~100 tokens)
- **At scale (10k messages/day):** ~$20/day for NLU
- **Optimization:** Cache common phrases in Redis; bypass GPT for exact matches (e.g., single-word items like "milk")

---

## 7. Outbound Messaging

### 7.1 Channel Adapters (Outbound)

```typescript
interface OutboundMessage {
  channel: 'sms' | 'email' | 'whatsapp';
  to: string;                    // phone or email
  body: string;
  listUrl?: string;              // appended as link
  groupParticipants?: string[];  // for group sends
}

// SMS (Twilio)
async function sendSMS(msg: OutboundMessage): Promise<void> {
  await twilioClient.messages.create({
    to: msg.to,
    from: BOB_TWILIO_NUMBER,
    body: `${msg.body}\n\n${msg.listUrl ?? ''}`.trim(),
  });
}

// Email (Mailgun)
async function sendEmail(msg: OutboundMessage): Promise<void> {
  await mailgun.messages.create(DOMAIN, {
    from: 'Bob <bob@buy-anything.com>',
    to: msg.to,
    cc: msg.groupParticipants?.join(','),
    subject: 'Your Shopping List Updated',
    text: `${msg.body}\n\nView your list: ${msg.listUrl}`,
    html: renderEmailTemplate(msg),
  });
}
```

### 7.2 Message Rate Limits

| Channel | Limit | Window |
|---------|-------|--------|
| SMS outbound per user | 5 messages | per hour |
| SMS outbound global | 100 messages | per minute (Twilio default) |
| Email outbound per user | 10 messages | per hour |
| Email outbound global | 300 messages | per minute (Mailgun tier) |

Bob batches list updates — if 3 items are added within 2 minutes, Bob sends one consolidated message rather than three.

**Batching implementation:** When a list item is added, set a Redis key `batch:{familyGroupId}` with 120s TTL. Append item to a Redis list `batchitems:{familyGroupId}`. A delayed BullMQ job fires after 120s, reads the batch, and sends one consolidated message.

---

## 8. Web Application (Next.js)

### 8.1 Pages

```
/                           → Landing page + "Enter your phone number to start"
/list/[listId]              → Shopping list view (public via signed token, claim requires auth)
/list/[listId]?token=xxx    → Signed read-only access link (shared via SMS/email)
/auth/verify                → OTP entry page
/wallet                     → Wallet balance + transaction history + payout button
/brand                      → Brand portal landing
/brand/dashboard            → Brand swap management + analytics
/brand/swaps/new            → Create new swap form
/r/[code]                   → Referral redirect → landing page with code stored in cookie
```

### 8.2 Shopping List View (`/list/[listId]`)

**Key UI Elements:**
- Search bar at top (calls `/api/lists/:listId/items/search`)
- List of items grouped by category
- Each item shows:
  - Item name + quantity + who added it
  - Expandable swap section showing up to 5 swaps ranked by value
  - Sponsored swap badge for brand-affiliated top spot
  - "Claim" button on each swap (requires auth)
- "Add Item" text input at bottom
- "Scan Receipt" button → opens camera / file upload
- Floating "Share List" button → copies signed link

### 8.3 Signed List Links

```typescript
// Generate signed URL for sharing
function generateListLink(listId: string, familyGroupId: string): string {
  const token = jwt.sign(
    { listId, familyGroupId, access: 'read' },
    LIST_LINK_SECRET,
    { expiresIn: '30d' }
  );
  return `${BASE_URL}/list/${listId}?token=${token}`;
}
```

---

## 9. Wallet & Transaction Engine

### 9.1 Transaction Creation (Double-Entry Pattern)

All wallet mutations go through a single function to ensure consistency:

```typescript
async function creditWallet(
  userId: string,
  amountCents: number,
  type: TransactionType,
  referenceType: string,
  referenceId: string,
  description: string,
  tx: PgTransaction  // must be called within a DB transaction
): Promise<Transaction> {
  // 1. Lock user row: SELECT ... FOR UPDATE
  const user = await tx.query('SELECT wallet_balance_cents FROM users WHERE id = $1 FOR UPDATE', [userId]);
  
  // 2. Calculate new balance
  const newBalance = user.wallet_balance_cents + amountCents;
  
  // 3. Insert transaction
  const txn = await tx.query(
    `INSERT INTO transactions (user_id, type, amount_cents, balance_after_cents, reference_type, reference_id, description)
     VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
    [userId, type, amountCents, newBalance, referenceType, referenceId, description]
  );
  
  // 4. Update user balance
  await tx.query('UPDATE users SET wallet_balance_cents = $1, updated_at = NOW() WHERE id = $2', [newBalance, userId]);
  
  return txn;
}
```

### 9.2 Redemption Credit Flow

When a receipt is validated and a claim is matched:

```typescript
async function processRedemption(claim: Claim, swap: Swap): Promise<void> {
  await db.transaction(async (tx) => {
    // 1. Credit user: swap discount value (e.g., $2.00 = 200 cents)
    const userCredit = swap.discount_value_cents;
    await creditWallet(claim.user_id, userCredit, 'redemption_credit', 'claim', claim.id, 
      `Redeemed: ${swap.description}`, tx);

    // 2. Calculate revenue: bid_amount from brand (e.g., $1.50 = 150 cents)
    const revenue = swap.bid_amount_cents;

    // 3. If user was referred, credit referrer 30% of revenue
    const user = await tx.query('SELECT referred_by_user_id FROM users WHERE id = $1', [claim.user_id]);
    if (user.referred_by_user_id) {
      const referralCredit = Math.floor(revenue * 0.30);
      await creditWallet(user.referred_by_user_id, referralCredit, 'referral_credit', 'claim', claim.id,
        `Referral earnings from redemption`, tx);
    }

    // 4. Update claim status
    await tx.query('UPDATE claims SET status = $1, redeemed_at = NOW(), receipt_id = $2 WHERE id = $3',
      ['redeemed', claim.receipt_id, claim.id]);

    // 5. Increment swap claims count
    await tx.query('UPDATE

swaps SET current_claims_count = current_claims_count + 1 WHERE id = $1', [swap.id]);

    // 6. Check if swap is exhausted
    if (swap.max_claims_total && swap.current_claims_count + 1 >= swap.max_claims_total) {
      await tx.query("UPDATE swaps SET status = 'exhausted' WHERE id = $1", [swap.id]);
    }
  });
}
```

### 9.3 Payout Flow

**Decision Point (DP-5):** Money transmission licensing. Recommended approach: use **Stripe Connect Express** accounts so Stripe holds funds as the regulated entity.

```typescript
async function requestPayout(userId: string, amountCents: number): Promise<Transaction> {
  // 1. Validate minimum payout threshold ($5.00 = 500 cents)
  if (amountCents < 500) throw new AppError('MINIMUM_PAYOUT_NOT_MET', 'Minimum payout is $5.00');

  // 2. Validate sufficient balance
  const user = await db.query('SELECT wallet_balance_cents, stripe_connect_id FROM users WHERE id = $1 FOR UPDATE', [userId]);
  if (user.wallet_balance_cents < amountCents) throw new AppError('INSUFFICIENT_BALANCE');

  // 3. If no Stripe Connect account, redirect user to onboarding
  if (!user.stripe_connect_id) throw new AppError('PAYOUT_SETUP_REQUIRED', 'Please link your bank account first.');

  // 4. Create Stripe Transfer
  const transfer = await stripe.transfers.create({
    amount: amountCents,
    currency: 'usd',
    destination: user.stripe_connect_id,
    transfer_group: `payout_${userId}_${Date.now()}`,
  });

  // 5. Debit wallet
  return await db.transaction(async (tx) => {
    return await creditWallet(userId, -amountCents, 'payout', 'stripe_transfer', transfer.id,
      `Payout to bank account`, tx);
  });
}
```

---

## 10. Affiliate / Referral Engine

### 10.1 Link Generation

Every user and brand gets a unique referral code at creation time.

```
Consumer referral URL:  https://buy-anything.com/r/{code}
Brand referral URL:     https://buy-anything.com/r/{code}?brand={brandId}
```

### 10.2 Attribution Flow

```typescript
// On /r/[code] page load:
// 1. Look up referral_links by code
// 2. Set cookie: bob_ref={code} (30-day expiry)
// 3. Increment click_count
// 4. Redirect to landing page

// On user signup (OTP verification):
// 1. Read bob_ref cookie
// 2. If present, look up referral_links by code
// 3. Set users.referred_by_user_id = referrer's user_id
// 4. Increment signup_count on referral_links
// 5. If brand referral: store brand_id on user record for sponsored swap placement
```

### 10.3 Brand Sponsored Placement

When a user was referred by a brand:

```typescript
// In swap-matching job (Section 5.4):
// After fetching swaps for a list item:
// 1. Check if the family group's creator was referred by a brand
// 2. If that brand has an active swap matching this item's category:
//    → Set rank = 0, is_sponsored = true on that list_item_swap
//    → This gives the referring brand the top spot each week
```

### 10.4 Revenue Share Calculation

```
Per redemption:
  Brand pays:           bid_amount_cents (e.g., $3.00 = 300 cents)
  User receives:        discount_value_cents (e.g., $2.50 = 250 cents)
  Groflo gross revenue: bid_amount_cents - discount_value_cents (e.g., $0.50 = 50 cents)
                        + Groflo's own margin from Groflo-sourced swaps

  If user was referred:
    Referrer gets:      30% of bid_amount_cents (e.g., $0.90 = 90 cents)
    Groflo net:         70% of margin
```

**Note:** The exact split between `bid_amount_cents` and `discount_value_cents` is set by the brand when creating the swap. Groflo's margin is the difference. The 30% referral share comes from Groflo's portion, not the user's discount.

---

## 11. Security & Privacy

### 11.1 Authentication

| Context | Method |
|---------|--------|
| Web app | Passwordless OTP via SMS or Email → JWT in HTTP-only, Secure, SameSite=Strict cookie |
| Messaging channels | Identity tied to phone/email; verified at onboarding via OTP |
| Brand portal | Same OTP flow + brand email verification (separate OTP to brand email) |
| Webhook endpoints | Provider signature validation (Twilio, Mailgun, Meta) |
| List share links | Signed JWT tokens with read-only scope, 30-day expiry |

### 11.2 Authorization

```typescript
// Middleware pattern
function requireAuth(handler): NextApiHandler {
  return async (req, res) => {
    const session = verifyJWT(req.cookies.bob_session);
    if (!session) return res.status(401).json({ error: 'UNAUTHORIZED' });
    req.userId = session.userId;
    return handler(req, res);
  };
}

function requireFamilyMember(handler): NextApiHandler {
  return async (req, res) => {
    const isMember = await db.query(
      'SELECT 1 FROM user_family_groups ufg JOIN shopping_lists sl ON sl.family_group_id = ufg.family_group_id WHERE ufg.user_id = $1 AND sl.id = $2',
      [req.userId, req.query.listId]
    );
    if (!isMember) return res.status(403).json({ error: 'FORBIDDEN' });
    return handler(req, res);
  };
}

function requireBrandAdmin(handler): NextApiHandler {
  return async (req, res) => {
    const brand = await db.query('SELECT 1 FROM brands WHERE id = $1 AND admin_user_id = $2', [req.query.brandId, req.userId]);
    if (!brand) return res.status(403).json({ error: 'FORBIDDEN' });
    return handler(req, res);
  };
}
```

### 11.3 PII Handling

| Data | Classification | Storage | Retention |
|------|---------------|---------|-----------|
| Phone numbers | PII | Encrypted at rest (PG column-level via pgcrypto or app-level AES-256) | Until account deletion |
| Email addresses | PII | Encrypted at rest | Until account deletion |
| Receipt images | Sensitive | S3/R2 with server-side encryption, private bucket | 90 days post-processing, then deleted |
| OCR results | Sensitive | JSONB in receipts table | 1 year |
| Wallet balances | Financial | PostgreSQL with row-level locking | Indefinite (regulatory) |
| Transaction history | Financial | Append-only, no deletes | 7 years (regulatory) |
| Message content | PII | Stored only as `raw_text` on list_items; full message bodies NOT persisted beyond processing | N/A |

### 11.4 Brand Data Isolation

- Brands never see individual user data
- Brand outreach emails contain only aggregate demand counts ("47 shoppers looking for yogurt this week")
- Brand dashboard shows only their own swap performance metrics
- No user phone/email is ever exposed to brands

---

## 12. Observability

### 12.1 Logging

**Structured JSON logs** via Pino (Node.js), shipped to a centralized log service (e.g., Datadog, Axiom, or Railway's built-in logs).

```typescript
// Every log entry includes:
{
  timestamp: string,
  level: 'info' | 'warn' | 'error',
  service: 'message-processor' | 'receipt-ocr' | 'web-api' | 'brand-outreach',
  traceId: string,          // propagated across queue jobs
  userId?: string,
  familyGroupId?: string,
  channel?: string,
  event: string,            // e.g., 'item_added', 'claim_created', 'receipt_processed'
  duration_ms?: number,
  error?: { message: string, stack: string },
  metadata?: Record<string, any>
}
```

### 12.2 Key Metrics (Prometheus / Datadog)

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `bob.messages.inbound.count` (by channel) | Counter | < 10/hr during business hours → alert |
| `bob.messages.processing.duration_ms` | Histogram | p95 > 5s → alert |
| `bob.nlu.intent.count` (by intent) | Counter | — |
| `bob.nlu.confidence` | Histogram | p50 < 0.6 → alert (model degradation) |
| `bob.receipts.ocr.duration_ms` | Histogram | p95 > 30s → alert |
| `bob.receipts.ocr.match_rate` | Gauge | < 50% → alert |
| `bob.claims.created.count` | Counter | — |
| `bob.redemptions.count` | Counter | — |
| `bob.redemptions.value_cents` | Counter | — |
| `bob.wallet.payout.count` | Counter | — |
| `bob.queue.depth` (by queue) | Gauge | > 1000 → alert |
| `bob.queue.failed.count` (by queue) | Counter | > 10/hr → alert |
| `bob.groflo.mcp.latency_ms` | Histogram | p95 > 3s → alert |
| `bob.groflo.mcp.error_rate` | Gauge | > 5% → alert |

### 12.3 Health Check

```
GET /api/health
→ {
    status: 'ok' | 'degraded' | 'down',
    checks: {
      database: 'ok' | 'error',
      redis: 'ok' | 'error',
      twilio: 'ok' | 'error',
      mailgun: 'ok' | 'error',
      groflo_mcp: 'ok' | 'error',
      queue_depth: number
    },
    version: string,
    uptime_seconds: number
  }
```

---

## 13. Performance SLOs

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Inbound message → acknowledgment (webhook response) | < 200ms | p99 |
| Inbound message → Bob's reply sent | < 10s | p95 |
| List item added → swaps attached | < 5s | p95 |
| Web list page load | < 1.5s | p95 (LCP) |
| Claim action (button click → confirmation) | < 500ms | p95 |
| Receipt upload → processing complete | < 45s | p95 |
| Receipt upload → processing complete | < 120s | p99 |

### 13.1 Scale Assumptions (First 6 Months)

| Dimension | Estimate |
|-----------|----------|
| Active family groups | 1,000 |
| Total users | 3,000 |
| Messages per day | 10,000 |
| List items per day | 3,000 |
| Claims per day | 500 |
| Receipts per day | 200 |
| Concurrent web users | 100 |

At this scale, a single Railway instance (2 vCPU, 4GB RAM) for the API + 1 worker instance for BullMQ queues is sufficient. PostgreSQL on Railway's managed offering. Redis on Upstash or Railway.

---

## 14. Error Handling & Edge Cases

### 14.1 Message Processing Failures

| Scenario | Handling |
|----------|----------|
| NLU returns low confidence (< 0.4) | Bob responds: "Not sure I caught that — did you want me to add something to the list? Just say 'add [item]'" |
| NLU timeout / OpenAI outage | Retry 2x. If still failing, fall back to keyword extraction regex. Log alert. |
| User sends message but isn't in any family group | Bob initiates onboarding: "Hey! I'm Bob. Want to start a family shopping list? Tell me who's in your group." |
| Unknown phone/email sends message to Bob | Create provisional user record, start onboarding flow |
| Duplicate message (carrier retry) | Deduplicate by `channelMessageId` with a 5-minute idempotency window in Redis |

### 14.2 Receipt Processing Failures

| Scenario | Handling |
|----------|----------|
| OCR can't parse receipt (blurry, crumpled) | Status → 'failed'. Bob responds: "I couldn't read that receipt. Can you take a clearer photo?" |
| Receipt parsed but no line items match any claims | Bob responds: "I processed your receipt but couldn't match it to your claimed deals. Items found: [list]. Claims pending: [list]." |
| Duplicate receipt fingerprint | Reject silently. Bob responds: "Looks like this receipt was already submitted." |
| Receipt date > 7 days old | Reject. Bob responds: "This receipt is too old. Receipts must be scanned within 7 days of purchase." |
| Partial match (2 of 3 claims matched) | Process the 2 matched claims. Notify user about the unmatched one with option to dispute. |

### 14.3 Concurrency & Race Conditions

| Scenario | Handling |
|----------|----------|
| Two family members claim the same swap simultaneously | `UNIQUE INDEX idx_claims_user_swap_list` prevents true duplicates. Different family members CAN claim the same swap (they're buying separate items). |
| Swap exhausted mid-claim | Check `current_claims_count < max_claims_total` inside a transaction with row lock on swaps. If exhausted, return error: "This deal just ran out!" |
| Wallet credited twice for same claim | `reference_id` + `reference_type` uniqueness check in application layer before calling `creditWallet`. |
| Multiple receipts submitted for same shopping trip | Fingerprint dedup catches exact duplicates. For different receipts from same store/date, allow — user may have split purchases. |

### 14.4 Channel-Specific Edge Cases

| Scenario | Handling |
|----------|----------|
| User removes Bob from group MMS | Bob loses ability to receive messages from that thread. Detected when outbound SMS fails. Bob sends 1:1 message to group owner: "Looks like I was removed from the group. Add me back or text me directly." |
| Email bounces (invalid family member email) | Mailgun bounce webhook → mark user email as invalid → notify group owner |
| User texts "STOP" (SMS opt-out) | Twilio handles automatically. Mark user as `sms_opted_out`. Communicate via email only. |
| MMS image that isn't a receipt (meme, photo) | GPT-4o Vision classifies image. If not a receipt, Bob responds: "That doesn't look like a receipt. Send me a photo of your grocery receipt to redeem your deals." |

---

## 15. Environment Configuration

```bash
# .env schema
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=        # Bob's SMS number

# Mailgun
MAILGUN_API_KEY=

MAILGUN_DOMAIN=buy-anything.com
MAILGUN_WEBHOOK_SIGNING_KEY=

# WhatsApp (V4)
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=

# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o         # for NLU + receipt OCR

# Groflo MCP
GROFLO_MCP_ENDPOINT=        # SSE or HTTP endpoint
GROFLO_MCP_API_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_CONNECT_CLIENT_ID=

# Auth
JWT_SECRET=                  # session tokens
LIST_LINK_SECRET=            # signed list share links
OTP_EXPIRY_SECONDS=300

# App
BASE_URL=https://buy-anything.com
NODE_ENV=production | staging | development

# Feature Flags
FF_WHATSAPP_ENABLED=false
FF_BRAND_AUTOBID_ENABLED=false
FF_RECEIPT_OCR_ENABLED=true
FF_PAYOUT_ENABLED=false      # disabled until Stripe Connect is live
```

### 15.1 Environment Parity

| Concern | Development | Staging | Production |
|---------|-------------|---------|------------|
| Database | Local PG via Docker | Railway PG (separate instance) | Railway PG (production) |
| Redis | Local Redis via Docker | Upstash (separate instance) | Upstash (production) |
| Twilio | Test credentials + magic numbers | Separate Twilio number | Production Twilio number |
| Mailgun | Sandbox domain (sandboxXXX.mailgun.org) | Subdomain (staging.buy-anything.com) | buy-anything.com |
| OpenAI | Same key, rate-limited | Same key | Same key, higher tier |
| Groflo MCP | Mock server (local) | Groflo sandbox (if available) | Groflo production |
| Stripe | Test mode keys | Test mode keys | Live mode keys |

---

## 16. Database Migrations Strategy

Using **Prisma Migrate** (or raw SQL migrations via `node-pg-migrate` if preferred for more control over the financial tables).

### 16.1 Migration Principles

1. **All migrations are forward-only** — no down migrations in production. Rollback via compensating migrations.
2. **Zero-downtime migrations** — no `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a default. Use the expand-contract pattern:
   - Step 1: Add nullable column
   - Step 2: Backfill data
   - Step 3: Add NOT NULL constraint
   - Step 4: Remove old column (if replacing)
3. **Financial tables are append-only** — `transactions` table never receives UPDATE or DELETE statements. Corrections are made via new `adjustment` type transactions.
4. **Migration naming:** `YYYYMMDDHHMMSS_description.sql`

### 16.2 Initial Migration Order

```
001_create_users.sql
002_create_family_groups.sql
003_create_user_family_groups.sql
004_create_shopping_lists.sql
005_create_list_items.sql
006_create_brands.sql
007_create_swaps.sql
008_create_list_item_swaps.sql
009_create_claims.sql
010_create_receipts.sql
011_create_transactions.sql
012_create_referral_links.sql
013_create_conversation_states.sql
014_create_indexes.sql
```

---

## 17. Testing Strategy

### 17.1 Unit Tests

| Module | Coverage Target | Key Cases |
|--------|----------------|-----------|
| Message Normalizer (per adapter) | 95% | Twilio group MMS parsing, Mailgun thread extraction, malformed payloads |
| NLU Intent Parser | 90% | All intent types, multi-item extraction, ambiguous messages, non-English input |
| Wallet / Transaction Engine | 100% | Credit, debit, insufficient balance, concurrent credits, referral calculation |
| Receipt Fingerprint Generator | 100% | Same receipt → same hash, different receipts → different hash, missing fields |
| Swap Matching / Ranking | 90% | Category match, keyword match, sponsored placement, exhausted swaps filtered |

### 17.2 Integration Tests

| Flow | What's Tested |
|------|--------------|
| SMS → Item Added → Swaps Attached | Twilio webhook → normalizer → NLU → Groflo MCP (mocked) → DB write → outbound SMS |
| Email → Item Added → Swaps Attached | Mailgun webhook → normalizer → same pipeline |
| Claim → Receipt → Redemption → Wallet Credit | Claim API → receipt upload → OCR (mocked GPT response) → matching → wallet credit → referral credit |
| Brand Registration → Swap Creation → Swap Appears on List | Brand auth → brand creation → swap creation → user adds matching item → swap shown |
| Referral → Signup → Attribution | Visit /r/code → cookie set → signup → referred_by set → redemption → referral credit |

### 17.3 End-to-End Tests (Playwright)

| Scenario | Steps |
|----------|-------|
| New user onboarding via web | Land on / → enter phone → receive OTP → verify → see empty list → add item → see swaps |
| Shopping list collaboration | User A adds item → User B opens same list link → sees item → claims swap |
| Receipt redemption | Claim swap → upload receipt image → see wallet balance increase |
| Brand portal | Register brand → verify email → create swap → see swap in dashboard |

### 17.4 Load Testing (k6)

Target: Sustain 100 concurrent users, 50 messages/second for 10 minutes without p95 latency degradation beyond SLO.

```javascript
// k6 script outline
export default function () {
  // Simulate inbound webhook
  http.post(`${BASE_URL}/api/webhooks/twilio`, twilioPayload, { headers: twilioSignatureHeaders });
  sleep(0.5);
  
  // Simulate list view
  http.get(`${BASE_URL}/api/lists/${testListId}?token=${signedToken}`);
  sleep(1);
  
  // Simulate claim
  http.post(`${BASE_URL}/api/claims`, claimPayload, { headers: authHeaders });
  sleep(2);
}
```

---

## 18. Rollout Plan

### Phase 1: Foundation (Weeks 1–3)

**Goal:** Email-only Bob with manual list management and Groflo MCP integration.

| Task | Effort |
|------|--------|
| PostgreSQL schema + migrations | 2 days |
| Mailgun inbound parse webhook + email adapter | 2 days |
| NLU intent classifier (GPT-4o, structured output) | 2 days |
| Groflo MCP client (item lookup + swap search) | 3 days |
| Conversation state machine (onboarding → active) | 2 days |
| Shopping list CRUD API | 2 days |
| Web list view (Next.js, read-only, no auth) | 2 days |
| Outbound email (list update notifications) | 1 day |
| BullMQ setup + message processing queue | 1 day |
| **Total** | **~17 days** |

**Deliverable:** User emails Bob → Bob creates list → items parsed → swaps shown on web list → Bob emails link back.

### Phase 2: SMS + Claims (Weeks 4–6)

| Task | Effort |
|------|--------|
| Twilio SMS adapter (inbound + outbound) | 2 days |
| Group MMS handling + testing across carriers | 3 days |
| OTP auth flow (web) | 2 days |
| Claim API + claim UI on list view | 2 days |
| User identity resolution (merge phone + email) | 2 days |
| Message batching (120s consolidation window) | 1 day |
| Family group management (add/remove members) | 2 days |
| **Total** | **~14 days** |

**Deliverable:** Users can text or email Bob. Claims work on web. Family groups functional.

### Phase 3: Receipts + Wallet + Brands (Weeks 7–10)

| Task | Effort |
|------|--------|
| Receipt upload (web + MMS image) | 2 days |
| GPT-4o Vision OCR pipeline | 3 days |
| Receipt fingerprinting + dedup | 1 day |
| Claim-to-receipt matching logic | 3 days |
| Wallet + transaction engine | 2 days |
| Stripe Connect integration (payouts) | 3 days |
| Brand registration + portal (Next.js) | 3 days |
| Brand swap creation UI | 2 days |
| Brand outreach queue (demand notifications) | 2 days |
| Groflo MCP redemption integration | 2 days |
| **Total** | **~23 days** |

**Deliverable:** Full redemption loop works. Brands can self-serve. Wallet payouts functional.

### Phase 4: Referrals + Polish (Weeks 11–12)

| Task | Effort |
|------|--------|
| Referral link generation + attribution | 2 days |
| Referral revenue share (30% auto-credit) | 1 day |
| Brand sponsored placement logic | 1 day |
| Brand dashboard (analytics, redemption stats) | 2 days |
| Rate limiting + abuse prevention | 1 day |
| Observability (structured logging, metrics, alerts) | 2 days |
| Security audit (PII encryption, auth hardening) | 2 days |
| Load testing + performance tuning | 2 days |
| **Total** | **~13 days** |

**Deliverable:** Production-ready system with referral engine, brand analytics, and operational observability.

### Phase 5: WhatsApp + Scale (Weeks 13–16)

| Task | Effort |
|------|--------|
| WhatsApp Business API integration | 5 days |
| WhatsApp adapter (inbound + outbound) | 3 days |
| Multi-number Twilio pool (if needed) | 2 days |
| Horizontal scaling (multiple worker instances) | 2 days |
| Database read replicas (if needed) | 1 day |
| CDN for list view (edge caching) | 1 day |
| **Total** | **~14 days** |

---

## 19. Open Decision Points Summary

| ID | Question | Impact | Default Assumption |
|----|----------|--------|--------------------|
| DP-1 | Group MMS reliability — fallback to 1:1 SMS? | Channel architecture | Test Group MMS first; fallback to 1:1 if > 10% message loss in carrier testing |
| DP-2 | Minimum wallet payout threshold | Stripe fees vs UX | $5.00 minimum |
| DP-3 | Groflo MCP exact tool interface and transport | Integration architecture | SSE transport with tools as specified in Section 4.3; adapt on receipt of actual spec |
| DP-4 | Receipt OCR fuzzy match confidence threshold | Redemption accuracy vs false negatives | 0.75; tune after 200 receipts processed |
| DP-5 | Money transmission — Stripe Connect Express vs custom | Legal/compliance | Stripe Connect Express (Stripe is regulated entity) |
| DP-6 | Grocery product taxonomy source | Item normalization quality | Groflo MCP provides this; if not, use Open Food Facts API as fallback |
| DP-7 | Brand outreach — automated vs manual for MVP | Brand acquisition velocity | Manual email templates triggered by demand queue for MVP; full automation in Phase 4 |
| DP-8 | List reset cadence — weekly auto vs user-triggered | UX | Weekly auto-reset (Sunday 8pm ET) with option to manually complete/archive |
| DP-9 | Multi-family support — can one user be in multiple family groups? | Data model | Yes, supported by many-to-many `user_family_groups` table |
| DP-10 | Receipt validation — what happens when OCR fails to match but user insists? | Support burden | Add "Dispute" button → flags for manual review queue (out of scope for MVP, handle via support email) |

---

## 20. Dependency Summary

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| Twilio (SMS/MMS) | External SaaS | Low — mature platform | Monitor delivery rates; fallback to Vonage if needed |
| Mailgun (Email) | External SaaS | Low | Fallback to SendGrid or AWS SES |
| OpenAI GPT-4o | External API | Medium — rate limits, cost, outage | Cache common NLU results; regex fallback for simple items; budget alerts |
| Groflo MCP | Partner API | **High** — spec not finalized | Build against assumed interface; adapter pattern allows swap |
| Stripe Connect | External SaaS | Low — mature platform | Delay payout feature until Connect is approved |
| Railway (hosting) | Infrastructure | Low | Standard PaaS; can migrate to Fly.io or AWS if needed |
| Apple iMessage (Group MMS) | Platform constraint | **High** — no API, behavior varies by carrier | Accept degraded experience; primary UX through web list |