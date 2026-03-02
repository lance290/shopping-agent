# WattData Integration Specification

**Status:** Draft  
**Created:** 2026-01-31  
**Last Updated:** 2026-01-31

---

## 1. Overview

WattData provides an MCP-based data platform for discovering vendor contacts. This spec defines how BuyAnything.ai integrates with WattData to enable proactive vendor outreach.

### 1.1 What WattData Provides

| Capability | Description |
|------------|-------------|
| **Semantic Search** | Query vendors using natural language |
| **Business Identities** | 60M+ verified business profiles |
| **Contact Data** | Email, phone, company info |
| **Intent Signals** | 50K+ daily signals per identity |
| **MCP Interface** | Direct AI agent integration |

### 1.2 Our Use Case

```
Buyer searches: "commercial HVAC maintenance in Austin"
    ↓
Agent extracts intent: { category: "hvac_service", location: "Austin, TX" }
    ↓
WattData query: "HVAC contractors in Austin, TX with commercial experience"
    ↓
Returns: 20 verified vendors with email/phone
    ↓
Agent sends personalized RFP to each vendor
    ↓
Vendor clicks magic link → submits quote → appears as tile
```

---

## 2. MCP Configuration

### 2.1 Connection Setup

```json
{
  "mcpServers": {
    "wattdata": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-wattdata"],
      "env": {
        "WATTDATA_API_KEY": "${WATTDATA_API_KEY}"
      }
    }
  }
}
```

### 2.2 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WATTDATA_API_KEY` | API authentication key | Yes |
| `WATTDATA_RATE_LIMIT` | Max queries per minute | No (default: 60) |

---

## 3. Query Interface

### 3.1 Vendor Discovery Query

```typescript
interface WattDataVendorQuery {
  description: string;           // Natural language description
  filters?: {
    business_type?: string;      // "service_provider", "retailer", "manufacturer"
    location?: {
      city?: string;
      state?: string;
      country?: string;
      radius_miles?: number;
    };
    employee_count?: {
      min?: number;
      max?: number;
    };
    revenue_range?: {
      min?: number;
      max?: number;
    };
    keywords?: string[];
    exclude_keywords?: string[];
  };
  limit?: number;                // Max results (default: 20, max: 100)
  include_intent_signals?: boolean;
}
```

### 3.2 Vendor Response

```typescript
interface WattDataVendor {
  id: string;
  business_name: string;
  description?: string;
  
  // Contact info
  email?: string;
  phone?: string;
  website?: string;
  
  // Location
  address?: {
    street?: string;
    city: string;
    state: string;
    zip?: string;
    country: string;
  };
  
  // Business details
  employee_count?: number;
  founded_year?: number;
  categories: string[];
  
  // Quality signals
  intent_score?: number;        // 0-1, how likely to respond
  verification_status: "verified" | "unverified";
  last_activity?: string;       // ISO date
}
```

### 3.3 Example Query

```typescript
// In BFF or Backend
const vendors = await mcpClient.call("wattdata", "search_businesses", {
  description: "Commercial HVAC contractors specializing in maintenance",
  filters: {
    business_type: "service_provider",
    location: {
      city: "Austin",
      state: "TX",
      radius_miles: 50
    },
    employee_count: { min: 5 }
  },
  limit: 20,
  include_intent_signals: true
});
```

---

## 4. Outreach Flow

### 4.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    BUYER COMPLETES RFP                          │
│  Row: "Commercial HVAC maintenance"                             │
│  Choice factors: { budget: "$5000-10000", timeline: "urgent" }  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WATTDATA QUERY                               │
│  Agent constructs semantic query from intent + location         │
│  Query: "HVAC contractors in Austin TX commercial maintenance"  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VENDOR FILTERING                             │
│  - Dedupe against already-contacted vendors                     │
│  - Filter by intent_score > 0.3                                 │
│  - Exclude opt-outs                                             │
│  - Limit to 20 per batch                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL GENERATION                             │
│  For each vendor:                                               │
│  - Generate personalized subject + body                         │
│  - Include: buyer needs, budget, timeline                       │
│  - Include: magic link to quote form                            │
│  - Include: unsubscribe link                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SEND VIA SENDGRID                            │
│  - Batch send with tracking                                     │
│  - Store message_id per vendor                                  │
│  - Update outreach_events table                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRACK ENGAGEMENT                             │
│  - Webhook: email opened                                        │
│  - Webhook: link clicked                                        │
│  - Event: quote submitted                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Trigger Conditions

Outreach is triggered when:
1. Buyer completes RFP (choice factors extracted)
2. Row has `outreach_enabled: true` (user opt-in)
3. Category suggests B2B/local services
4. Fewer than 3 e-commerce results found

### 4.3 Rate Limits

| Scope | Limit | Window |
|-------|-------|--------|
| Per row | 50 vendors | 24 hours |
| Per user | 200 vendors | 24 hours |
| Platform | 10,000 vendors | 24 hours |
| WattData API | 60 queries | 1 minute |

---

## 5. Email Templates

### 5.1 Initial Outreach

**Subject:** `{{buyer_name}} is looking for {{service_category}} - Quote Request`

**Body:**
```
Hi {{vendor_name}},

A buyer on BuyAnything.ai is looking for {{service_category}} in {{location}} and your business came up as a great match.

**What they need:**
{{rfp_summary}}

**Budget:** {{budget_range}}
**Timeline:** {{timeline}}

If you're interested, you can submit a quote directly:
{{quote_link}}

No account required - just answer a few questions and submit your offer.

Best,
The BuyAnything.ai Agent

---
You received this because your business matches buyer needs on BuyAnything.ai.
Unsubscribe: {{unsubscribe_link}}
```

### 5.2 Reminder (48h after no response)

**Subject:** `Reminder: Quote request from {{buyer_name}} - {{service_category}}`

**Body:**
```
Hi {{vendor_name}},

Just a quick follow-up - {{buyer_name}} is still looking for {{service_category}} and hasn't received a quote from you yet.

Submit your quote: {{quote_link}}

This request expires in {{days_remaining}} days.

Best,
The BuyAnything.ai Agent

---
Unsubscribe: {{unsubscribe_link}}
```

---

## 6. Compliance

### 6.1 CAN-SPAM Requirements

| Requirement | Implementation |
|-------------|----------------|
| Clear sender identification | "BuyAnything.ai Agent" with valid address |
| Honest subject lines | Must reflect content |
| Unsubscribe mechanism | One-click unsubscribe link |
| Honor opt-outs within 10 days | Immediate via database flag |
| Physical address | Include in footer |

### 6.2 Opt-Out Handling

```sql
-- On unsubscribe click
UPDATE outreach_events 
SET opt_out = TRUE 
WHERE vendor_email = ?;

-- Insert into global opt-out list
INSERT INTO email_opt_outs (email, opted_out_at, source)
VALUES (?, NOW(), 'unsubscribe_link');
```

### 6.3 Data Retention

| Data Type | Retention | Deletion |
|-----------|-----------|----------|
| Vendor contact info | 90 days | Auto-purge |
| Outreach events | 1 year | Anonymize after |
| Opt-out list | Permanent | Never delete |

---

## 7. Backend Implementation

### 7.1 New Files

```
apps/backend/
├── outreach/
│   ├── __init__.py
│   ├── wattdata_client.py      # MCP client wrapper
│   ├── email_templates.py      # Jinja2 templates
│   ├── outreach_service.py     # Orchestration
│   └── sendgrid_client.py      # Email delivery
```

### 7.2 WattData Client

```python
# apps/backend/outreach/wattdata_client.py

class WattDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.wattdata.ai/v1"
    
    async def search_vendors(
        self,
        description: str,
        location: Optional[dict] = None,
        filters: Optional[dict] = None,
        limit: int = 20
    ) -> List[WattDataVendor]:
        """Query WattData for matching vendors."""
        # Implementation via MCP or REST API
        pass
    
    async def get_vendor_details(self, vendor_id: str) -> WattDataVendor:
        """Get full details for a specific vendor."""
        pass
```

### 7.3 Outreach Service

```python
# apps/backend/outreach/outreach_service.py

class OutreachService:
    def __init__(
        self,
        wattdata: WattDataClient,
        sendgrid: SendGridClient,
        db: Session
    ):
        self.wattdata = wattdata
        self.sendgrid = sendgrid
        self.db = db
    
    async def trigger_outreach(self, row_id: int) -> OutreachResult:
        """Main entry point for vendor outreach."""
        row = await self.db.get(Row, row_id)
        
        # 1. Build query from row intent
        query = self._build_vendor_query(row)
        
        # 2. Query WattData
        vendors = await self.wattdata.search_vendors(**query)
        
        # 3. Filter already-contacted and opt-outs
        vendors = await self._filter_vendors(vendors, row_id)
        
        # 4. Generate and send emails
        results = []
        for vendor in vendors[:20]:
            result = await self._send_outreach(row, vendor)
            results.append(result)
        
        # 5. Update row status
        await self._update_row_status(row_id, len(results))
        
        return OutreachResult(sent=len(results), vendors=results)
```

---

## 8. API Endpoints

### 8.1 Trigger Outreach

```
POST /rows/{row_id}/outreach

Request:
{
  "max_vendors": 20,        // Optional, default 20
  "include_reminder": true  // Optional, schedule 48h reminder
}

Response:
{
  "status": "initiated",
  "vendors_contacted": 18,
  "skipped": {
    "already_contacted": 2,
    "opted_out": 0
  }
}
```

### 8.2 Get Outreach Status

```
GET /rows/{row_id}/outreach/status

Response:
{
  "status": "in_progress",
  "total_sent": 18,
  "opened": 5,
  "clicked": 3,
  "quotes_received": 1,
  "last_activity": "2026-01-31T15:30:00Z"
}
```

### 8.3 Webhook: Email Events

```
POST /webhooks/sendgrid

{
  "event": "open",
  "email": "vendor@example.com",
  "message_id": "sg_abc123",
  "timestamp": 1706720400
}
```

---

## 9. Metrics & Monitoring

### 9.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Outreach delivery rate | >98% | <95% |
| Email open rate | >25% | <15% |
| Click-through rate | >10% | <5% |
| Quote submission rate | >5% | <2% |
| Opt-out rate | <1% | >3% |

### 9.2 Logging

```python
logger.info(
    "Outreach sent",
    extra={
        "event": "outreach_sent",
        "row_id": row_id,
        "vendor_email": vendor.email,
        "vendor_source": "wattdata",
        "message_id": result.message_id
    }
)
```

---

## 10. Testing

### 10.1 Mock WattData Responses

```python
# tests/fixtures/wattdata_responses.py

MOCK_VENDORS = [
    {
        "id": "wd_123",
        "business_name": "Austin HVAC Pro",
        "email": "contact@austinhvac.example.com",
        "phone": "+15125551234",
        "address": {
            "city": "Austin",
            "state": "TX"
        },
        "categories": ["hvac", "commercial"],
        "intent_score": 0.8,
        "verification_status": "verified"
    }
]
```

### 10.2 Integration Tests

- Query WattData with test credentials
- Verify vendor filtering logic
- Test email template rendering
- Test SendGrid delivery (sandbox mode)
- Verify webhook processing
