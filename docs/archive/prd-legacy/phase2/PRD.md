# Phase 2 PRD: Marketplace Experience & Seller Loop

**Status:** Draft  
**Author:** Cascade + Lance  
**Created:** 2026-01-31  
**Last Updated:** 2026-02-03

---

## 1. Executive Summary

### 1.1 Context

Phase 1 delivered the **Search Architecture v2**: a 5-layer pipeline with intent extraction, multi-provider sourcing, streaming results, and observability. The buyer can now search, see results from multiple providers stream in, and organize items into project-based rows.

Phase 2 transforms this search tool into a **marketplace** by:
1. Adding transparency (tile provenance)
2. Enabling collaboration (share links, likes, comments)
3. Opening the seller side (quote intake, outreach)
4. Closing the loop (checkout, contracts)

### 1.2 North Star

> **"Reverse eBay for the AI agent era"** — Buyers post needs; sellers compete to win.

### 1.3 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time-to-first-offer | <30s | From query to first tile displayed |
| Seller response rate | >20% | % of outreach emails that result in a quote |
| Viral coefficient (K) | >1.2 | New users acquired per transaction |
| Intent-to-close rate | >10% | % of searches resulting in checkout/contract |

---

## 2. What's Built (Phase 1 Complete)

| Component | Status | Notes |
|-----------|--------|-------|
| Intent Extraction | ✅ | BFF extracts SearchIntent via LLM |
| Provider Adapters | ✅ | Rainforest, Google CSE, SerpAPI, SearchAPI |
| Streaming Search | ✅ | SSE progressive loading, provider status badges |
| Result Normalization | ✅ | NormalizedResult schema, canonical URLs |
| Project Hierarchy | ✅ | Rows grouped under projects |
| Observability | ✅ | Structured logging, metrics tracking |
| Price Filtering | ✅ | Native + post-filter hybrid |
| Bid Persistence | ✅ | Upsert by canonical URL |

---

## 3. Phase 2 Scope

### 3.1 In Scope

| Feature | Priority | Effort |
|---------|----------|--------|
| **Tile Detail & Provenance** | P0 | S |
| **Likes Persistence** | P0 | S |
| **Comments Persistence** | P0 | S |
| **Share Links (Copy URL)** | P0 | S |
| **Merchant Registry** | P1 | M |
| **Seller Quote Intake** | P1 | M |
| **WattData Outreach** | P1 | L |
| **Email Handoff (MVP Closing)** | P1 | S |
| **Unified Closing (Stripe)** | P2 | M |
| **DocuSign Contracts** | P2 | L |

### 3.2 Out of Scope (Phase 3+)

- Full seller dashboard/portal (basic merchant dashboard IS in scope)
- Merchant verification/vetting
- Inventory management
- Logistics/shipping integration
- Mobile app
- Internationalization

---

## 4. Feature Specifications

### 4.1 Tile Detail & Provenance

**Goal:** When a buyer clicks a tile, they see WHY it was recommended.

**User Story:**
> As a buyer, I want to click on a product tile and see the choice factors that match my requirements, plus the chat history that led to this recommendation.

**Requirements:**

| ID | Requirement |
|----|-------------|
| TD-01 | Clicking a tile opens a slide-out detail panel |
| TD-02 | Panel shows: title, price, merchant, image, rating, reviews |
| TD-03 | Panel shows "Why recommended" section with matched choice factors |
| TD-04 | Panel shows relevant chat excerpts (if any) |
| TD-05 | Panel includes "Like", "Comment", "Select" actions |

**Data Model:**
```typescript
interface TileProvenance {
  matched_features: Record<string, string>;  // e.g., {"frame_material": "carbon"}
  intent_match_score: number;                // 0-1
  price_match: "within" | "below" | "above" | "unknown";
  chat_excerpts?: string[];                  // Relevant Q&A snippets
}
```

**Implementation:**
- Backend: Add `provenance` field to search response
- Frontend: Create `TileDetailPanel` component
- Store provenance in bid metadata for persistence

---

### 4.2 Likes & Comments Persistence

**Goal:** Buyers can like and comment on tiles; state persists across sessions.

**Current State:** Backend models exist (`Like`, `Comment` tables). Frontend has UI but persistence is partially tested.

**Requirements:**

| ID | Requirement |
|----|-------------|
| LC-01 | Like state syncs to backend on click |
| LC-02 | Like state restored on page reload |
| LC-03 | Comments saved with user attribution |
| LC-04 | Comments visible to collaborators |
| LC-05 | Like/comment counts shown on tile |

**API Endpoints (existing):**
- `POST /bids/{bid_id}/like`
- `DELETE /bids/{bid_id}/like`
- `POST /bids/{bid_id}/comments`
- `GET /bids/{bid_id}/comments`

**Work Needed:**
- Click-test and fix any bugs
- Add like/comment counts to tile display
- Ensure auth context propagates correctly

---

### 4.3 Share Links

**Goal:** Buyers can share their project/row/tile with collaborators via URL.

**User Story:**
> As a buyer, I want to copy a link to my project workspace so my team can review and vote on selections.

**Requirements:**

| ID | Requirement |
|----|-------------|
| SL-01 | "Copy Link" button on project, row, and tile |
| SL-02 | Shared link opens directly to the shared item |
| SL-03 | Viewer can see tiles but cannot edit (unless invited) |
| SL-04 | Share tracking captures referral attribution |

**URL Structure:**
```
/p/{project_id}                    # Project view
/p/{project_id}/r/{row_id}         # Row within project
/p/{project_id}/r/{row_id}/b/{bid_id}  # Specific tile
```

**Implementation:**
- Add shareable slugs or use existing IDs
- Create public viewer role (read-only)
- Track share events for viral coefficient measurement

---

### 4.4 Seller Quote Intake

**Goal:** Sellers can submit bids/quotes that appear as tiles in the buyer's row.

**User Story:**
> As a seller (HVAC contractor), I receive an RFP email, click a link, answer key questions, and submit my quote — all without creating an account.

**Requirements:**

| ID | Requirement |
|----|-------------|
| QI-01 | Seller receives structured RFP via email |
| QI-02 | Email contains magic link to quote submission form |
| QI-03 | Form pre-populated with buyer's choice factors as questions |
| QI-04 | Seller submits: price, description, images, links |
| QI-05 | Submitted quote appears as tile in buyer's row |
| QI-06 | Buyer notified of new quote |

**Data Model:**
```python
@dataclass
class SellerQuote:
    id: str
    row_id: int
    seller_email: str
    seller_name: str
    seller_company: Optional[str]
    price: float
    currency: str = "USD"
    description: str
    answers: Dict[str, str]  # Responses to choice factor questions
    attachments: List[str]   # URLs to images/docs
    submitted_at: datetime
    status: str  # "pending", "accepted", "rejected"
```

**Implementation:**
- New table: `seller_quotes`
- New endpoint: `POST /quotes/submit?token={magic_link_token}`
- Quote → Bid conversion on submission
- Email notification to buyer

---

### 4.5 WattData Proactive Outreach

**Goal:** Agent automatically discovers and contacts relevant vendors for buyer RFPs.

**User Story:**
> As a buyer searching for "commercial HVAC maintenance in Austin", I want the agent to find and contact local HVAC contractors on my behalf.

**Requirements:**

| ID | Requirement |
|----|-------------|
| WD-01 | Agent queries WattData for vendors matching buyer intent |
| WD-02 | WattData returns: business name, email, phone, category |
| WD-03 | Agent sends personalized RFP email to each vendor |
| WD-04 | Outreach tracked per row (who was contacted, when) |
| WD-05 | Vendor response flows into Quote Intake |
| WD-06 | Buyer sees "Outreach in progress" status |

**WattData Integration:**
```typescript
// MCP query example
const vendors = await wattdata.query({
  description: "HVAC contractors in Austin, TX",
  filters: {
    business_type: "service_provider",
    location: { city: "Austin", state: "TX" },
    employee_count: { min: 5 }
  },
  limit: 20
});
```

**Outreach Flow:**
1. Buyer completes RFP (choice factors extracted)
2. Agent queries WattData for matching vendors
3. For each vendor: generate personalized email with RFP summary
4. Send via SendGrid/Twilio
5. Track delivery, opens, clicks
6. Magic link in email → Quote Intake form

**Compliance:**
- CAN-SPAM: Include unsubscribe link
- Rate limit outreach (max 50/day per row)
- Store consent/opt-out status

See: [wattdata-integration.md](./wattdata-integration.md) for full spec.

---

### 4.6 Merchant Registry

**Goal:** Build a preferred seller network that gets priority matching over cold outreach.

**User Story:**
> As a roofing contractor, I want to register on the platform so I receive RFP notifications for jobs in my area and get priority placement over competitors.

**Requirements:**

| ID | Requirement |
|----|-------------|
| MR-01 | Merchant self-registration with business profile |
| MR-02 | Category and service area selection |
| MR-03 | Priority matching: registered merchants notified before WattData outreach |
| MR-04 | "Verified Partner" badge on registered merchant quotes |
| MR-05 | Basic merchant dashboard to view RFPs and submitted quotes |
| MR-06 | Notification preferences (email frequency, RFP types) |

**Matching Waterfall:**
1. **Registered Merchants** (category + location match) → immediate notification
2. **WattData Outreach** (if <5 registered matches) → cold outreach
3. **Amazon/Serp** (always included) → product results

See: [prd-merchant-registry.md](./prd-merchant-registry.md) for full spec.

---

### 4.7 Email Handoff (MVP Closing)

**Goal:** Enable transaction completion via email introduction — lightweight alternative to contracts.

**User Story:**
> As a buyer, after selecting a quote for my private jet trip, I want the seller and I to be introduced via email so we can finalize the deal directly.

**Requirements:**

| ID | Requirement |
|----|-------------|
| EH-01 | "Select" on quote triggers confirmation modal |
| EH-02 | Introduction email sent to both buyer and seller |
| EH-03 | Emails include contact info, deal summary, next steps |
| EH-04 | Buyer can "Mark as Closed" for tracking |
| EH-05 | Transaction status tracked (selected → introduced → closed) |

**When to Use:**
- Service quotes (HVAC, roofing, private jets, etc.)
- Transactions where contract/payment varies by deal
- MVP closing before DocuSign/Stripe integration

See: [prd-email-handoff.md](./prd-email-handoff.md) for full spec.

---

### 4.8 Unified Closing Layer

**Goal:** Buyers can complete purchases directly within the platform.

##### 4.8.1 Retail Checkout (Stripe)

**Requirements:**

| ID | Requirement |
|----|-------------|
| UC-01 | "Buy Now" button on eligible tiles |
| UC-02 | Checkout modal with Stripe Elements |
| UC-03 | Payment success creates `clickout_event` |
| UC-04 | Affiliate attribution tracked |

**Implementation:**
- Stripe Checkout Session for affiliate purchases
- For direct purchases: Stripe Connect (future)

#### 4.8.2 B2B Contracts (DocuSign)

**Requirements:**

| ID | Requirement |
|----|-------------|
| DS-01 | "Select" on B2B tile triggers contract flow |
| DS-02 | Agent generates contract from template |
| DS-03 | DocuSign envelope sent to buyer + seller |
| DS-04 | Signed contract stored and linked to bid |

**B2B Threshold:**
- Transactions >$1,000 OR
- Seller marked as "contract required" OR
- Buyer requests contract

---

## 5. Identity & Permissions Model

### 5.1 User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **Buyer** | Primary user creating RFPs | Create projects/rows, search, like, comment, select, checkout |
| **Collaborator** | Invited to view/vote | View project, like, comment |
| **Seller** | Responds to RFPs | Submit quotes, view own quotes |
| **Registered Merchant** | Proactive seller | All Seller permissions + receive RFP notifications, dashboard access |
| **Admin** | Platform operator | All |

### 5.2 Authentication Methods

| Method | Use Case |
|--------|----------|
| Email magic link | Primary auth for buyers |
| OAuth (Google) | Optional convenience |
| Quote magic link | Seller quote submission (no account required) |
| Share link + optional login | Collaborator access |

### 5.3 Permission Matrix

| Action | Buyer (owner) | Collaborator | Seller | Anonymous |
|--------|---------------|--------------|--------|-----------|
| View project | ✅ | ✅ | ❌ | Via share link |
| Create row | ✅ | ❌ | ❌ | ❌ |
| Like tile | ✅ | ✅ | ❌ | ❌ |
| Comment | ✅ | ✅ | ❌ | ❌ |
| Select tile | ✅ | ❌ | ❌ | ❌ |
| Submit quote | ❌ | ❌ | ✅ | Via magic link |
| Checkout | ✅ | ❌ | ❌ | ❌ |

---

## 6. Database Changes

### 6.1 New Tables

```sql
-- Seller quotes (before conversion to bid)
CREATE TABLE seller_quotes (
    id SERIAL PRIMARY KEY,
    row_id INTEGER REFERENCES rows(id),
    token VARCHAR(64) UNIQUE NOT NULL,  -- Magic link token
    seller_email VARCHAR(255) NOT NULL,
    seller_name VARCHAR(255),
    seller_company VARCHAR(255),
    price DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    answers JSONB,  -- Choice factor responses
    attachments JSONB,  -- URLs
    submitted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Outreach tracking
CREATE TABLE outreach_events (
    id SERIAL PRIMARY KEY,
    row_id INTEGER REFERENCES rows(id),
    vendor_email VARCHAR(255) NOT NULL,
    vendor_name VARCHAR(255),
    vendor_source VARCHAR(50),  -- 'wattdata', 'manual'
    message_id VARCHAR(255),  -- SendGrid message ID
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    quote_submitted_at TIMESTAMP,
    opt_out BOOLEAN DEFAULT FALSE
);

-- Merchant registry
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    website VARCHAR(255),
    notification_prefs JSONB,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'suspended'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE merchant_categories (
    merchant_id INTEGER REFERENCES merchants(id),
    category VARCHAR(100) NOT NULL,
    PRIMARY KEY (merchant_id, category)
);

CREATE TABLE merchant_service_areas (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER REFERENCES merchants(id),
    area_type VARCHAR(20) NOT NULL,  -- 'zip', 'radius', 'region'
    area_value VARCHAR(255) NOT NULL
);

-- Deal handoffs (email closing)
CREATE TABLE deal_handoffs (
    id SERIAL PRIMARY KEY,
    row_id INTEGER REFERENCES rows(id),
    quote_id INTEGER REFERENCES seller_quotes(id),
    buyer_email_sent_at TIMESTAMP,
    seller_email_sent_at TIMESTAMP,
    buyer_opened_at TIMESTAMP,
    seller_opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    deal_value DECIMAL(12,2)
);

-- Share links
CREATE TABLE share_links (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    resource_type VARCHAR(20) NOT NULL,  -- 'project', 'row', 'bid'
    resource_id INTEGER NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0
);
```

### 6.2 Existing Table Changes

```sql
-- Add provenance to bids
ALTER TABLE bids ADD COLUMN provenance JSONB;
ALTER TABLE bids ADD COLUMN is_seller_quote BOOLEAN DEFAULT FALSE;
ALTER TABLE bids ADD COLUMN seller_quote_id INTEGER REFERENCES seller_quotes(id);
ALTER TABLE bids ADD COLUMN merchant_id INTEGER REFERENCES merchants(id);

-- Add outreach status to rows
ALTER TABLE rows ADD COLUMN outreach_status VARCHAR(20);  -- 'none', 'in_progress', 'complete'
ALTER TABLE rows ADD COLUMN outreach_count INTEGER DEFAULT 0;
```

---

## 7. API Endpoints

### 7.1 New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/bids/{bid_id}/provenance` | Get tile provenance data |
| POST | `/rows/{row_id}/outreach` | Trigger vendor outreach |
| GET | `/rows/{row_id}/outreach/status` | Get outreach progress |
| POST | `/quotes/submit` | Submit seller quote (magic link auth) |
| GET | `/quotes/{token}` | Get quote form data |
| POST | `/share` | Create share link |
| GET | `/s/{token}` | Resolve share link |
| POST | `/checkout/session` | Create Stripe checkout |
| POST | `/merchants/register` | Merchant self-registration |
| GET | `/merchants/dashboard` | Merchant dashboard data |
| PUT | `/merchants/profile` | Update merchant profile |
| POST | `/quotes/{quote_id}/select` | Select quote, trigger email handoff |
| POST | `/deals/{deal_id}/close` | Mark deal as closed |

### 7.2 Updated Endpoints

| Method | Path | Changes |
|--------|------|---------|
| GET | `/bids` | Include `provenance`, `like_count`, `comment_count` |
| GET | `/rows/{row_id}` | Include `outreach_status` |

---

## 8. Implementation Phases

### Phase 2a: Buyer Engagement (1-2 weeks)

**Goal:** Complete the buyer-side experience.

| Task | Effort | Dependencies |
|------|--------|--------------|
| Tile Detail Panel | S | - |
| Provenance data in search response | S | - |
| Likes click-test + fixes | S | - |
| Comments click-test + fixes | S | - |
| Share links (copy URL) | S | - |

**Exit Criteria:**
- Buyer can click tile, see provenance
- Likes/comments persist across reload
- Share link copies to clipboard

### Phase 2b: Seller Loop (2-3 weeks)

**Goal:** Enable sellers to respond to buyer RFPs.

| Task | Effort | Dependencies |
|------|--------|--------------|
| Seller quote schema + table | S | - |
| Quote submission form | M | Quote schema |
| Magic link auth for sellers | S | - |
| Quote → Bid conversion | S | Quote form |
| WattData MCP integration | M | - |
| Outreach email templates | S | WattData |
| Outreach tracking | M | Email templates |

**Exit Criteria:**
- Seller can submit quote via magic link
- Quote appears as tile in buyer's row
- Agent can query WattData and send outreach

### Phase 2c: Closing Layer (2-3 weeks)

**Goal:** Complete transactions within platform.

| Task | Effort | Dependencies |
|------|--------|--------------|
| Stripe checkout integration | M | - |
| Affiliate tracking | S | Stripe |
| DocuSign envelope generation | M | - |
| Contract template system | M | DocuSign |
| B2B threshold detection | S | - |

**Exit Criteria:**
- Retail purchase completes via Stripe
- B2B selection triggers DocuSign flow
- Transaction events tracked

---

## 9. Competitive Positioning

### 9.1 PartFinder Comparison

Phase 2 delivers **feature parity with PartFinder** (B2B industrial parts sourcing startup) while maintaining our consumer UX advantage.

| PartFinder Feature | Our Phase 2 Equivalent |
|-------------------|------------------------|
| AI Email Agent | WattData Outreach + SendGrid |
| RFQ to multiple suppliers | `POST /rows/{row_id}/outreach` |
| Centralized comms dashboard | Outreach status on row |
| Quote submission (magic link) | Seller Quote Intake |
| Response tracking | `outreach_events` table |
| Deal closing | Email Handoff + DocuSign |

### 9.2 Our Differentiators

**Features we have that PartFinder doesn't:**
- **Merchant Registry** — Two-sided marketplace; they only do cold outreach
- **Service Provider Network** — Category taxonomy (home, auto, professional, travel, events)
- **Social Features** — Likes, comments, collaborative decision-making
- **Viral Mechanics** — Share links with referral tracking
- **Consumer Marketplace** — Real-time Amazon, Google Shopping, eBay integration
- **Conversational UX** — Chat-driven interface vs. form-based

### 9.3 B2B Expansion Path

Phase 2 positions us for B2B without additional work:

| Capability | Status |
|------------|--------|
| RFQ Automation | ✅ WattData Outreach |
| Quote Intake | ✅ Magic link flow |
| Merchant Network | ✅ Registry + taxonomy |
| Deal Closing | ✅ Email Handoff + DocuSign |
| Service Categories | ✅ Home, auto, professional, travel, events |

**Monetization paths (from Merchant Registry):**
- Lead fees (charge merchant per RFP notification)
- Success fees (% of closed deals)
- Premium tier (priority placement, more leads)

### 9.4 Remaining Gaps (Phase 3+)

| Gap | Priority | Notes |
|-----|----------|-------|
| ERP Integrations | Low | SAP/NetSuite for enterprise stickiness |
| Parts-specific AI | Low | Technical spec understanding for industrial |
| Photo-based Search | Medium | Upload image → find part |
| Automated Negotiation | Low | AI counter-offers |

See [Competitive Analysis](../Competitive_Analysis_PartFinder.md) for full details.

---

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Low seller response to outreach | High | Medium | A/B test messaging; add phone follow-up |
| WattData rate limits | Medium | Low | Cache results; batch queries |
| Spam complaints from outreach | High | Medium | Strict CAN-SPAM compliance; quality scoring |
| Quote spam from bad actors | Medium | Low | Rate limit per IP; CAPTCHA on form |
| Stripe/DocuSign API downtime | High | Low | Graceful degradation; retry queues |

---

## 11. Success Criteria

Phase 2 is complete when:

- [ ] Buyer can click tile and see provenance
- [ ] Likes and comments persist across sessions
- [ ] Share links work for projects, rows, tiles
- [ ] Seller can submit quote via magic link
- [ ] Quote appears as tile in buyer's row
- [ ] Agent queries WattData for vendors
- [ ] Outreach emails sent with tracking
- [ ] Retail checkout works via Stripe
- [ ] B2B contract flow works via DocuSign
- [ ] Viral coefficient measurable via share tracking

---

## 12. Appendix

### 12.1 Related Documents

- [Parent PRD](../marketplace-pivot/parent.md)
- [Search Architecture v2 PRD](../search-architecture-v2/PRD.md)
- [WattData Integration Spec](./wattdata-integration.md)
- [Quote Intake Schema](./quote-intake-schema.md)
- [Competitive Analysis: PartFinder](../Competitive_Analysis_PartFinder.md)
- [Phase 3 Roadmap](./phase3-roadmap.md)

### 12.2 References

- [WattData](https://www.wattdata.ai/) — Vendor discovery MCP (we are investors)
- [Stripe Checkout](https://stripe.com/docs/checkout)
- [DocuSign eSignature API](https://developers.docusign.com/)
- [SendGrid API](https://docs.sendgrid.com/)
- [PartFinder Pitch Deck](../PartFinder_PitchDeck.pdf) — Competitor reference
