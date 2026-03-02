# Seller Quote Intake Schema

**Status:** Draft  
**Created:** 2026-01-31  
**Last Updated:** 2026-01-31

---

## 1. Overview

This document defines the data model and flow for seller quote submission. Sellers receive an RFP via email, click a magic link, and submit a quote that appears as a tile in the buyer's row.

---

## 2. Data Model

### 2.1 SellerQuote

```python
@dataclass
class SellerQuote:
    """A quote submitted by a seller in response to a buyer's RFP."""
    
    # Identity
    id: int
    token: str                      # Magic link token (unique)
    row_id: int                     # Target buyer row
    
    # Seller info
    seller_email: str
    seller_name: Optional[str]
    seller_company: Optional[str]
    seller_phone: Optional[str]
    seller_website: Optional[str]
    
    # Quote details
    price: Decimal
    currency: str = "USD"
    price_type: str                 # "fixed", "hourly", "per_unit", "negotiable"
    price_notes: Optional[str]      # e.g., "Includes installation"
    
    # Description
    title: str                      # Short title for the quote
    description: str                # Detailed description
    
    # Choice factor responses
    answers: Dict[str, str]         # Responses to buyer's choice factors
    
    # Attachments
    attachments: List[QuoteAttachment]
    
    # Metadata
    submitted_at: Optional[datetime]
    status: str                     # "draft", "submitted", "accepted", "rejected", "withdrawn"
    created_at: datetime
    updated_at: datetime
    
    # Conversion
    bid_id: Optional[int]           # Set when converted to bid


@dataclass
class QuoteAttachment:
    """File or link attached to a quote."""
    id: int
    quote_id: int
    type: str                       # "image", "document", "link"
    url: str
    filename: Optional[str]
    mime_type: Optional[str]
    uploaded_at: datetime
```

### 2.2 Database Schema

```sql
CREATE TABLE seller_quotes (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    row_id INTEGER NOT NULL REFERENCES rows(id) ON DELETE CASCADE,
    
    -- Seller info
    seller_email VARCHAR(255) NOT NULL,
    seller_name VARCHAR(255),
    seller_company VARCHAR(255),
    seller_phone VARCHAR(50),
    seller_website VARCHAR(500),
    
    -- Quote details
    price DECIMAL(12, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    price_type VARCHAR(20) DEFAULT 'fixed',
    price_notes TEXT,
    
    -- Description
    title VARCHAR(500),
    description TEXT,
    
    -- Choice factor responses (JSONB)
    answers JSONB DEFAULT '{}',
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',
    submitted_at TIMESTAMP,
    
    -- Conversion tracking
    bid_id INTEGER REFERENCES bids(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_seller_quotes_token ON seller_quotes(token);
CREATE INDEX idx_seller_quotes_row ON seller_quotes(row_id);
CREATE INDEX idx_seller_quotes_email ON seller_quotes(seller_email);
CREATE INDEX idx_seller_quotes_status ON seller_quotes(status);

CREATE TABLE quote_attachments (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER NOT NULL REFERENCES seller_quotes(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    url TEXT NOT NULL,
    filename VARCHAR(255),
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_quote_attachments_quote ON quote_attachments(quote_id);
```

---

## 3. Quote Submission Flow

### 3.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                 SELLER RECEIVES EMAIL                           │
│  Subject: "Quote Request: Commercial HVAC in Austin"            │
│  Contains magic link: /quotes/submit?token=abc123               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SELLER CLICKS LINK                              │
│  GET /quotes/abc123                                             │
│  Returns: Row context, choice factors, seller pre-fill          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 QUOTE FORM DISPLAYED                            │
│  - Buyer's need summary                                         │
│  - Choice factor questions (from SearchIntent)                  │
│  - Price input (with type selector)                             │
│  - Description textarea                                         │
│  - File/link attachments                                        │
│  - Seller contact info (pre-filled from outreach)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SELLER SUBMITS QUOTE                            │
│  POST /quotes/submit                                            │
│  Validation: required fields, price format, attachments         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 QUOTE → BID CONVERSION                          │
│  Create Bid from SellerQuote                                    │
│  Set bid.is_seller_quote = true                                 │
│  Set bid.seller_quote_id = quote.id                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 BUYER NOTIFICATION                              │
│  Email: "New quote received for [Row Title]"                    │
│  In-app: Badge on row, new tile appears                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Magic Link Token

```python
def create_quote_token(row_id: int, seller_email: str) -> str:
    """Create a magic link token for quote submission."""
    token = secrets.token_urlsafe(32)
    
    quote = SellerQuote(
        token=token,
        row_id=row_id,
        seller_email=seller_email,
        status="draft"
    )
    db.add(quote)
    db.commit()
    
    return token

# Token URL format
# https://buyanything.ai/quotes/{token}
```

### 3.3 Token Validation

```python
async def validate_quote_token(token: str) -> SellerQuote:
    """Validate quote token and return quote context."""
    quote = await db.query(SellerQuote).filter_by(token=token).first()
    
    if not quote:
        raise HTTPException(404, "Quote not found")
    
    if quote.status not in ("draft", "submitted"):
        raise HTTPException(400, "Quote no longer editable")
    
    # Check if row still exists and accepts quotes
    row = await db.get(Row, quote.row_id)
    if not row or row.status == "closed":
        raise HTTPException(400, "This request is no longer accepting quotes")
    
    return quote
```

---

## 4. API Endpoints

### 4.1 Get Quote Form

```
GET /quotes/{token}

Response:
{
  "quote": {
    "id": 123,
    "seller_email": "contractor@example.com",
    "seller_name": null,
    "status": "draft"
  },
  "row_context": {
    "title": "Commercial HVAC maintenance",
    "description": "Annual maintenance for 10,000 sq ft office",
    "choice_factors": [
      {"key": "service_area", "label": "Service Area Coverage", "type": "text"},
      {"key": "response_time", "label": "Emergency Response Time", "type": "select", "options": ["<2 hours", "2-4 hours", "Same day", "Next day"]},
      {"key": "certifications", "label": "Certifications", "type": "multiselect", "options": ["EPA 608", "NATE", "HVAC Excellence"]}
    ],
    "budget_range": "$5,000 - $10,000",
    "timeline": "Within 2 weeks"
  },
  "buyer": {
    "name": "John (Acme Corp)",
    "location": "Austin, TX"
  }
}
```

### 4.2 Submit Quote

```
POST /quotes/submit

Request:
{
  "token": "abc123",
  "seller_name": "Mike Johnson",
  "seller_company": "Austin HVAC Pro",
  "seller_phone": "+1-512-555-1234",
  "seller_website": "https://austinhvacpro.com",
  "title": "Annual HVAC Maintenance Package",
  "price": 7500.00,
  "currency": "USD",
  "price_type": "fixed",
  "price_notes": "Includes 2 visits per year, parts extra",
  "description": "Comprehensive maintenance program including...",
  "answers": {
    "service_area": "Austin metro, 50 mile radius",
    "response_time": "<2 hours",
    "certifications": ["EPA 608", "NATE"]
  },
  "attachments": [
    {"type": "link", "url": "https://austinhvacpro.com/commercial"},
    {"type": "document", "url": "https://...uploaded.pdf", "filename": "service_agreement.pdf"}
  ]
}

Response:
{
  "success": true,
  "quote_id": 123,
  "bid_id": 456,
  "message": "Quote submitted successfully"
}
```

### 4.3 Update Quote (Before Acceptance)

```
PUT /quotes/{token}

Request:
{
  "price": 7000.00,
  "price_notes": "Revised pricing with 7% discount"
}

Response:
{
  "success": true,
  "quote_id": 123
}
```

### 4.4 Withdraw Quote

```
DELETE /quotes/{token}

Response:
{
  "success": true,
  "message": "Quote withdrawn"
}
```

---

## 5. Quote → Bid Conversion

### 5.1 Conversion Logic

```python
async def convert_quote_to_bid(quote: SellerQuote) -> Bid:
    """Convert a submitted quote into a Bid for display."""
    
    # Build canonical URL from quote
    canonical_url = f"quote://{quote.id}"
    
    # Check for existing bid
    existing = await db.query(Bid).filter_by(
        row_id=quote.row_id,
        canonical_url=canonical_url
    ).first()
    
    if existing:
        # Update existing bid
        existing.title = quote.title
        existing.price = quote.price
        existing.currency = quote.currency
        existing.description = quote.description
        existing.seller_name = quote.seller_company or quote.seller_name
        existing.updated_at = datetime.utcnow()
        bid = existing
    else:
        # Create new bid
        bid = Bid(
            row_id=quote.row_id,
            title=quote.title,
            price=quote.price,
            currency=quote.currency,
            url=quote.seller_website or "",
            canonical_url=canonical_url,
            source="seller_quote",
            merchant_name=quote.seller_company or quote.seller_name,
            merchant_domain=extract_domain(quote.seller_website),
            image_url=get_first_image(quote.attachments),
            description=quote.description,
            is_seller_quote=True,
            seller_quote_id=quote.id,
            provenance={
                "type": "seller_quote",
                "seller_email": quote.seller_email,
                "answers": quote.answers,
                "submitted_at": quote.submitted_at.isoformat()
            }
        )
        db.add(bid)
    
    # Link quote to bid
    quote.bid_id = bid.id
    quote.status = "submitted"
    quote.submitted_at = datetime.utcnow()
    
    await db.commit()
    return bid
```

### 5.2 Bid Display

Seller quotes appear as tiles with special styling:
- Badge: "Seller Quote"
- Contact info available on tile detail
- "Message Seller" action
- Price type indicator (fixed/hourly/negotiable)

---

## 6. Choice Factor Integration

### 6.1 Extracting Questions from SearchIntent

```python
def build_quote_questions(row: Row) -> List[QuoteQuestion]:
    """Build quote form questions from row's SearchIntent."""
    questions = []
    
    intent = row.search_intent
    if not intent:
        return default_questions()
    
    # Add questions for each feature
    for key, value in intent.get("features", {}).items():
        questions.append(QuoteQuestion(
            key=key,
            label=humanize_key(key),  # "frame_material" → "Frame Material"
            type="text",
            hint=f"Buyer specified: {value}"
        ))
    
    # Add standard questions
    questions.extend([
        QuoteQuestion(key="availability", label="Availability", type="text"),
        QuoteQuestion(key="warranty", label="Warranty/Guarantee", type="text"),
        QuoteQuestion(key="experience", label="Relevant Experience", type="textarea"),
    ])
    
    return questions
```

### 6.2 QuoteQuestion Schema

```typescript
interface QuoteQuestion {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "multiselect" | "number";
  required?: boolean;
  hint?: string;
  options?: string[];  // For select/multiselect
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
}
```

---

## 7. Notifications

### 7.1 Buyer Notification (New Quote)

**Email:**
```
Subject: New quote received for "Commercial HVAC maintenance"

Hi {{buyer_name}},

Good news! {{seller_company}} has submitted a quote for your request.

**Quote Summary:**
- Price: ${{price}} ({{price_type}})
- Seller: {{seller_name}} from {{seller_company}}

View the full quote and compare with other options:
{{row_link}}

Best,
The BuyAnything.ai Team
```

**In-App:**
- Badge on row: "1 new quote"
- New tile appears with animation
- Toast notification: "New quote from [Seller]"

### 7.2 Seller Notification (Quote Status)

**On Acceptance:**
```
Subject: Your quote was accepted! 🎉

Hi {{seller_name}},

Great news! {{buyer_name}} has accepted your quote for "{{row_title}}".

Next steps:
1. The buyer will reach out to finalize details
2. You may be asked to sign a contract via DocuSign

View details: {{quote_link}}
```

**On Rejection:**
```
Subject: Quote update for "{{row_title}}"

Hi {{seller_name}},

The buyer has selected a different option for "{{row_title}}".

Don't worry - there are more opportunities! We'll notify you of 
relevant requests that match your expertise.

Best,
The BuyAnything.ai Team
```

---

## 8. Validation Rules

### 8.1 Required Fields

| Field | Required | Validation |
|-------|----------|------------|
| `title` | Yes | 5-200 characters |
| `price` | Yes | > 0, max 2 decimals |
| `description` | Yes | 20-5000 characters |
| `seller_name` | Yes | 2-100 characters |
| `seller_email` | Yes | Valid email format |

### 8.2 Price Validation

```python
def validate_price(price: Decimal, price_type: str) -> None:
    if price <= 0:
        raise ValidationError("Price must be greater than 0")
    
    if price > 10_000_000:
        raise ValidationError("Price exceeds maximum allowed")
    
    if price_type == "hourly" and price > 10_000:
        raise ValidationError("Hourly rate seems unusually high")
```

### 8.3 Attachment Validation

| Type | Max Size | Allowed Formats |
|------|----------|-----------------|
| Image | 5 MB | jpg, png, gif, webp |
| Document | 10 MB | pdf, doc, docx |
| Link | N/A | Valid URL |

---

## 9. Security

### 9.1 Token Security

- Tokens are 256-bit random strings
- Single-use for initial access, then session-based
- Expire after 7 days of inactivity
- Rate limited: 10 submissions per email per hour

### 9.2 Input Sanitization

```python
def sanitize_quote_input(data: dict) -> dict:
    """Sanitize user input before storage."""
    return {
        "title": bleach.clean(data["title"]),
        "description": bleach.clean(data["description"], tags=ALLOWED_TAGS),
        "answers": {k: bleach.clean(str(v)) for k, v in data["answers"].items()},
        # ... other fields
    }
```

### 9.3 Spam Prevention

- CAPTCHA on quote form (hCaptcha)
- Rate limiting per IP and email
- Content analysis for spam patterns
- Manual review queue for flagged quotes
