# PRD: Autonomous Outreach

**Status**: Draft  
**Date**: 2026-02-15  
**Origin**: User Intention Audit (Gaps 6, 7) + `Autonomous_Outreach_Strategy.md`  
**Priority**: P0 — transforms BuyAnything from "search engine" to "procurement agent"  
**Depends on**: PRD_Desire_Classification (for routing service/bespoke/high-value requests)

---

## 1. The Problem (Spirit)

Today, BuyAnything finds vendors. Then it stops. The user stares at a list of 11 charter operators and thinks: *"Now what? How do I contact these people? What do I say? How do I compare their quotes?"*

The system did the *letter* of its job (found vendors) but violated the *spirit* (the user wanted to *charter a jet*, not *receive a list*).

**The real pain** (from the private jet project):
1. Shopping Agent surfaces 11 charter providers
2. The EA manually figures out how to contact each one
3. EA writes 11 individual emails from scratch
4. EA tracks who replied, who didn't, who quoted what
5. EA compares quotes manually in a spreadsheet
6. EA negotiates with 2-3 finalists
7. EA reports the best option to the client

**Steps 2-6 are the pain.** The system handed the user a list and said "good luck." That's a genie loophole.

### The Genie Test

> "I found vendors for you." — Yes, but the user wanted a jet booking, not a vendor list. Finding vendors is step 1 of 7. The system stopped at step 1 and called it done.

---

## 2. The Vision (What "Done" Looks Like)

The user says: **"I need a light jet from Teterboro to Aspen on March 15 for 4 passengers."**

The system:
1. Classifies as **Service** tier (→ PRD_Desire_Classification)
2. Finds 11 matching charter operators via vendor directory
3. For each vendor, **drafts a personalized outreach message** using the request details
4. Presents the EA with an **Outreach Queue**: 11 pre-written emails, each with [Preview] [Edit] [Approve]
5. EA reviews, tweaks tone, clicks **[Approve All Emails]** — 2 minutes instead of 45
6. System sends approved emails from a dedicated domain
7. Vendor replies flow into the app, LLM extracts quote data
8. EA sees a **live comparison table**: vendor, price, aircraft, status, response thread
9. System drafts follow-ups for non-responsive vendors
10. System drafts negotiation emails using competitive pricing data
11. EA approves final recommendation to client

**The EA goes from *doing everything* to *reviewing everything*. The judgment stays human. The grunt work disappears.**

---

## 3. Three Levels (Build Incrementally)

### Level 1: Draft & Send (MVP — start here)

The agent drafts personalized outreach per vendor. EA reviews and approves. Agent sends approved emails.

**What the agent does:**
- Drafts outreach messages using request details + vendor profile
- Discovers/stores each vendor's preferred contact method
- Sends emails when EA approves
- For non-email channels: prepares message for EA to send manually

**What the EA does:**
- Reviews and edits drafts (tone, personal touches)
- Approves outbound emails with one click
- Handles phone/WhatsApp/manual channels with agent-prepared talking points

**Spirit check:** The EA's time drops from ~45 min (writing 11 emails) to ~5 min (reviewing 11 pre-written emails).

### Level 2: Track & Compare

Vendor replies flow into the app. LLM extracts structured data. Live comparison table.

**What the agent does:**
- Each request gets a dedicated reply-to address (`jet-7f3a@quotes.buyanything.com`)
- Vendor email replies arrive in-app automatically
- LLM extracts: price, availability, aircraft type, terms, expiration
- Builds live comparison table
- Flags non-responsive vendors, drafts follow-ups

**What the EA does:**
- Views all responses in one place (no inbox hunting)
- Manually logs non-email responses (phone notes, WhatsApp quotes)
- Reviews comparison table
- Approves follow-ups

**Spirit check:** The EA never has to ask "wait, what did NetJets quote again?" — it's all in one place, structured and comparable.

### Level 3: Negotiate (EA-Supervised)

The agent drafts negotiation responses using competitive data.

**What the agent does:**
- Drafts counter-offers: "You quoted $42k but we have a $38.5k offer for similar aircraft"
- Uses category-specific knowledge (e.g., "ask about empty leg availability")
- Drafts follow-ups on timing and terms

**What the EA does:**
- **Always reviews before sending** — negotiation is high-stakes
- Adds relationship context the agent doesn't have
- Decides strategy (which vendors to push, when to stop)
- Makes final recommendation

**Two modes:**
1. **Supervised** (default): Every negotiation email requires EA approval
2. **Semi-autonomous** (opt-in, later): EA sets guardrails ("target below $35k, max 2 rounds"), agent executes within bounds

---

## 4. Technical Design

### 4.1 Data Model

#### Outreach Campaign

```sql
CREATE TABLE outreach_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    row_id UUID NOT NULL REFERENCES rows(id),
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
        -- draft, active, paused, completed, cancelled
    request_summary TEXT NOT NULL,
        -- LLM-generated summary of what the user wants
    structured_constraints JSONB,
        -- from Desire Classification: {origin, destination, date, pax, ...}
    action_budget INT NOT NULL DEFAULT 20,
        -- max vendor contacts for this campaign
    actions_used INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Outreach Message

```sql
CREATE TABLE outreach_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES outreach_campaigns(id),
    vendor_id UUID NOT NULL REFERENCES vendors(id),
    bid_id UUID REFERENCES bids(id),
        -- links to the bid/offer that triggered outreach
    direction VARCHAR(10) NOT NULL,
        -- outbound, inbound
    channel VARCHAR(20) NOT NULL,
        -- email, web_form, whatsapp, phone, manual
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
        -- draft, ea_review, approved, sent, delivered, replied, bounced, failed
    subject TEXT,
    body TEXT NOT NULL,
    body_html TEXT,
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    reply_to_address VARCHAR(255),
        -- campaign-specific: jet-7f3a@quotes.buyanything.com
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    metadata JSONB,
        -- delivery IDs, tracking pixels, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Quote (extracted from vendor replies)

```sql
CREATE TABLE outreach_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES outreach_campaigns(id),
    vendor_id UUID NOT NULL REFERENCES vendors(id),
    message_id UUID REFERENCES outreach_messages(id),
        -- the inbound message this was extracted from
    entry_method VARCHAR(20) NOT NULL,
        -- auto_extracted, ea_manual
    price DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'USD',
    availability TEXT,
    terms TEXT,
    expiration_date DATE,
    structured_data JSONB,
        -- category-specific: {aircraft: "CJ3+", seats: 7, wifi: true, ...}
    confidence FLOAT,
        -- LLM extraction confidence (auto_extracted only)
    is_finalist BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.2 Backend Services

#### OutreachService

```
apps/backend/services/outreach_service.py
```

Responsibilities:
- `draft_campaign(row, decision)` → Creates campaign + drafts for all matching vendors
- `approve_message(message_id, ea_edits)` → Marks message as approved, queues for sending
- `approve_all(campaign_id)` → Bulk approve all draft messages
- `pause_campaign(campaign_id)` → Emergency stop — hold all queued messages
- `process_inbound(email_payload)` → Match inbound email to campaign, extract quote data
- `draft_followup(campaign_id, vendor_id)` → Draft follow-up for non-responsive vendor
- `draft_negotiation(campaign_id, vendor_id, strategy)` → Draft counter-offer

#### EmailDeliveryService

```
apps/backend/services/email_delivery.py
```

Wraps an email provider (SendGrid, Postmark, or AWS SES):
- `send(message)` → Delivers approved email
- `process_webhook(payload)` → Handles delivery/open/bounce events
- `process_inbound_parse(payload)` → Receives vendor replies

#### QuoteExtractionService

```
apps/backend/services/quote_extraction.py
```

LLM-powered extraction from vendor reply text:
- `extract_quote(email_text, campaign_context)` → Returns structured quote data
- Uses the campaign's `structured_constraints` to know what fields to extract
- Returns confidence score; low-confidence extractions are flagged for EA review

### 4.3 LLM Prompts

#### Outreach Draft Prompt

```
You are drafting an outreach email on behalf of an executive assistant.

Request details:
{structured_constraints}

Vendor: {vendor.name} ({vendor.description})
Vendor contact: {vendor.contact_email}

Write a professional, concise email requesting availability and pricing.
Include all relevant details from the request.
Sign as: {ea_name}, Executive Assistant

Tone: Professional but warm. This is a business inquiry, not a cold sales email.
Do NOT include made-up details. Only use information provided.
```

#### Quote Extraction Prompt

```
Extract structured quote data from this vendor reply.

Campaign context: {campaign.request_summary}
Expected fields: {fields_for_category}

Vendor reply:
---
{email_text}
---

Return JSON with extracted fields and a confidence score (0-1).
If a field is not mentioned, return null (not a guess).
```

### 4.4 Frontend Components

#### Outreach Queue (Level 1)

New component on the Row detail page, visible when `desire_tier` is service/bespoke/high_value:

```
┌──────────────────────────────────────────────────────────────────┐
│ Outreach Queue                                    [Approve All] │
│                                                   [Pause All]   │
├──────────────┬──────────────┬────────────────────────────────────┤
│ Vendor       │ Channel      │ Actions                            │
├──────────────┼──────────────┼────────────────────────────────────┤
│ TurnKey Jets │ 📧 Email     │ [Preview] [Edit] [Approve] [Skip] │
│ NetJets      │ 📧 Email     │ [Preview] [Edit] [Approve] [Skip] │
│ Wheels Up    │ 🌐 Web Form  │ [Preview] [Edit] [Approve] [Skip] │
│ VistaJet     │ 📱 WhatsApp  │ [Copy to Clipboard]               │
│ Flexjet      │ 📞 Phone     │ [View Talking Points]             │
├──────────────┴──────────────┴────────────────────────────────────┤
│ Budget: 5 of 20 contacts used                                   │
└──────────────────────────────────────────────────────────────────┘
```

#### Comparison Dashboard (Level 2)

```
┌──────────────┬──────────┬──────────┬──────────┬───────────────┐
│ Vendor       │ Price    │ Aircraft │ Status   │ Actions       │
├──────────────┼──────────┼──────────┼──────────┼───────────────┤
│ TurnKey Jets │ $42,000  │ CJ3+    │ ✅ Quoted │ [View Thread] │
│ NetJets      │ $38,500  │ Phenom  │ ✅ Quoted │ [View Thread] │
│ Wheels Up    │ —        │ —       │ ⏳ Sent   │ [Follow Up]   │
│ VistaJet     │ $45,000  │ Global  │ ✅ Quoted │ [Logged by EA]│
│ Flexjet      │ —        │ —       │ 📞 Called │ [Add Notes]   │
├──────────────┴──────────┴──────────┴──────────┴───────────────┤
│ Best deal: NetJets at $38,500 (Phenom 300)                    │
│ [Share with Client] [Export PDF]                               │
└───────────────────────────────────────────────────────────────┘
```

### 4.5 Inbound Email Architecture

```
Vendor replies to: jet-7f3a@quotes.buyanything.com
        │
        ▼
  Email Provider (SendGrid Inbound Parse / Postmark / SES)
        │
        ▼
  POST /webhooks/inbound-email
        │
        ▼
  Match to campaign by reply-to address
        │
        ▼
  Store as outreach_message (direction: inbound)
        │
        ▼
  LLM quote extraction (async)
        │
        ▼
  Store outreach_quote + notify EA
```

Each campaign gets a unique reply-to address. This makes matching trivial and keeps vendor threads separate.

---

## 5. Safety Model

### 5.1 Rate Limits
- Max **20** vendor contacts per campaign (configurable)
- Max **3** follow-ups per vendor
- Max **3** negotiation rounds per vendor
- All limits visible to EA as "action budget"

### 5.2 EA Always in the Loop
- **Level 1-2**: Every outbound email requires EA approval. No exceptions.
- **Level 3 Supervised**: Every negotiation draft requires EA review.
- **Level 3 Semi-autonomous** (future): EA sets guardrails, agent executes within bounds, EA can pause anytime.

### 5.3 Emergency Stop
- **[Pause All]** button on every campaign — one click, everything stops
- All queued messages held, all follow-ups paused
- Resumes only on explicit EA action

### 5.4 Audit Trail
- Every outbound message: timestamp, content, recipient, delivery status
- Every inbound response: timestamp, content, extracted data
- Every EA action: approval, edit, skip, manual entry
- Client-shareable audit trail for transparency

---

## 6. The Data Flywheel (Moat)

Every outreach cycle makes the next one better:

| Data | How It Improves the System |
|---|---|
| **Vendor contact method** | Next time, we already know email vs. phone vs. WhatsApp |
| **Vendor response time** | Rank responsive vendors higher; set follow-up timing |
| **Category-specific templates** | "For jets, always include route, dates, pax, aircraft preference" |
| **Quote normalization patterns** | Compare apples-to-apples across wildly different pricing structures |
| **Negotiation playbooks** | "For jets, ask about empty legs. For diamonds, ask about GIA vs. Rapaport." |
| **EA edit patterns** | What edits do EAs make? Use that to improve drafts. |

---

## 7. Success Metrics

### Letter Metrics
- Emails sent per campaign (target: > 5 vendor contacts per service request)
- Email delivery rate (target: > 95%)
- Quote extraction accuracy (target: > 80% vs EA manual review)

### Spirit Metrics
- **EA time savings**: Time from "request received" to "all vendors contacted" (baseline: 45 min manual → target: < 5 min with approve-all)
- **Response rate**: What % of contacted vendors reply with a quote? (Baseline: unmeasured. Target: track and optimize.)
- **Desire fulfillment rate**: Of service-tier requests, what % end with a vendor selection? (Baseline: ~0% — system stops at "here's a list." Target: > 30%)
- **Client satisfaction**: Does the EA feel like the system helped them *do their job*, or just added more work?

---

## 8. Rollout Plan

### Phase 1: Draft & Send MVP (3-4 weeks)
- Outreach campaign and message data models
- LLM outreach draft generation
- Outreach Queue UI (draft → review → approve flow)
- Email delivery integration (SendGrid or Postmark)
- Campaign-specific reply-to addresses
- [Pause All] emergency stop

### Phase 2: Track & Compare (3-4 weeks)
- Inbound email processing (webhook)
- LLM quote extraction pipeline
- Manual entry UI for phone/WhatsApp/in-person quotes
- Comparison dashboard UI
- Follow-up draft generation
- Notification system (in-app + email to EA)

### Phase 3: Negotiate (4-6 weeks, after Phase 2 has production data)
- Negotiation draft generation using competitive pricing data
- Category-specific negotiation knowledge
- Supervised mode: every draft requires EA approval
- Semi-autonomous mode (opt-in): guardrails + execution within bounds

---

## 9. What We Don't Build (Yet)

- **Automated web form submission** — too fragile, too many edge cases. EA handles manually for now.
- **WhatsApp/Telegram integration** — clipboard copy is good enough for Level 1. API integration later.
- **Phone call AI** — way too risky for HNWI context. EA makes calls with agent-prepared talking points.
- **Auto-negotiation without EA review** — never in Level 1-2. Opt-in only in Level 3.

---

## 10. Dependencies

- **Upstream**: PRD_Desire_Classification (tells us when to activate outreach vs. web search)
- **Parallel**: PRD_Quantum_ReRanking (ranks vendor results before outreach drafting)
- **Infrastructure**: Email delivery provider (SendGrid/Postmark/SES), mail domain for inbound

---

## 11. The Spirit Check

Before shipping any milestone, ask:

> If the EA still has to write emails from scratch after we ship this — have we shipped anything of value?

> If the EA can review and approve 11 pre-written emails in 2 minutes — have we transformed their workflow?

> If a vendor replies with a quote and the EA has to hunt through their inbox to find it — have we solved the comparison problem?

The outreach system exists to close the gap between "here are some vendors" and "here is the best option, ready to book." That's the spirit. Everything else is just the letter.
