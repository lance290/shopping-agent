# Plan: Seller Quote Intake System

## Goal
Build a magic-link-based quote submission system that converts seller quotes to Bids, integrating with existing buyer search interface to advance multi-provider procurement by enabling persistable, negotiable offers from multiple sellers.

## Constraints
- Integrate with existing Clerk auth patterns for consistency
- Single quote per seller per Row (deduplication)
- Bids must appear as tiles in existing buyer Row interface
- Mobile-first responsive design for business users
- Include file attachment infrastructure (per PRD requirements)

## Technical Approach

### Backend Changes

#### Database Schema (Alembic migration)
```sql
-- Extend existing rows table with choice factors
ALTER TABLE rows ADD COLUMN choice_factors JSONB DEFAULT '[]'::jsonb;
-- Structure: [{"id": "delivery_time", "question": "Delivery timeline?", "type": "select", "options": ["1-2 weeks", "2-4 weeks", "1+ months"], "required": true}]

-- New seller quotes table (temporary storage before Bid conversion)
CREATE TABLE seller_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(255) UNIQUE NOT NULL,
    row_id UUID NOT NULL REFERENCES rows(id) ON DELETE CASCADE,
    seller_email VARCHAR(255) NOT NULL,
    seller_name VARCHAR(255) NOT NULL,
    seller_company VARCHAR(255),
    price_amount DECIMAL(10,2),
    price_type VARCHAR(20) CHECK (price_type IN ('fixed', 'hourly', 'negotiable')),
    description TEXT,
    choice_factor_answers JSONB,
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN ('submitted', 'converted', 'archived')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(row_id, seller_email)
);

-- New bids table (converted from seller quotes)
CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    row_id UUID NOT NULL REFERENCES rows(id) ON DELETE CASCADE,
    seller_id UUID,  -- NULL for quote-originated bids until seller creates account
    seller_name VARCHAR(255) NOT NULL,
    seller_company VARCHAR(255),
    price_amount DECIMAL(10,2),
    price_type VARCHAR(20) CHECK (price_type IN ('fixed', 'hourly', 'negotiable')),
    description TEXT,
    choice_factor_answers JSONB,
    source VARCHAR(20) DEFAULT 'quote' CHECK (source IN ('quote', 'direct')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'accepted', 'rejected', 'withdrawn')),
    negotiation_thread_id UUID,  -- Reference to future negotiation system
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Separate attachment tables for cleaner relationships
CREATE TABLE quote_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES seller_quotes(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    upload_type VARCHAR(20) CHECK (upload_type IN ('image', 'document', 'link')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bid_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bid_id UUID NOT NULL REFERENCES bids(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    upload_type VARCHAR(20) CHECK (upload_type IN ('image', 'document', 'link')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Update rows table for bid count
ALTER TABLE rows ADD COLUMN bid_count INTEGER DEFAULT 0;

-- Critical performance indexes
CREATE INDEX idx_seller_quotes_token ON seller_quotes(token);
CREATE INDEX idx_seller_quotes_row_id ON seller_quotes(row_id);
CREATE INDEX idx_seller_quotes_email_row ON seller_quotes(seller_email, row_id);
CREATE INDEX idx_bids_row_id ON bids(row_id);
CREATE INDEX idx_bids_status ON bids(status);
CREATE INDEX idx_quote_attachments_quote_id ON quote_attachments(quote_id);
CREATE INDEX idx_bid_attachments_bid_id ON bid_attachments(bid_id);
```

#### FastAPI Routes
```python
# New seller quote routes (/routes/seller_quotes.py)
# GET /seller-quotes/{token} - Load quote form with Row context
# POST /seller-quotes/{token} - Submit quote with file uploads
# POST /seller-quotes/{token}/attachments - Upload files during quote submission

# New bid routes (/routes/bids.py)
# GET /rows/{row_id}/bids - List bids for buyers (extends existing functionality)
# POST /bids/{bid_id}/accept - Accept bid (future buyer action)
# POST /bids/{bid_id}/negotiate - Start negotiation thread (future enhancement)

# Extend existing rows routes (/routes/rows.py)
# GET /rows/{row_id} - Include bid_count in response
```

#### Models
```python
# /models/row.py (extend existing)
class Row(Base):
    choice_factors = Column(JSONB, default=list)  # Add to existing model
    bid_count = Column(Integer, default=0)
    bids = relationship("Bid", back_populates="row")

# /models/seller_quote.py (new)
class SellerQuote(Base):
    __tablename__ = "seller_quotes"
    row = relationship("Row")
    attachments = relationship("QuoteAttachment", cascade="all, delete-orphan")

# /models/bid.py (new)
class Bid(Base):
    __tablename__ = "bids"
    negotiation_thread_id = Column(UUID)  # Future negotiation workflow hook
    row = relationship("Row", back_populates="bids")
    attachments = relationship("BidAttachment", cascade="all, delete-orphan")

# /models/quote_attachment.py (new)
class QuoteAttachment(Base):
    __tablename__ = "quote_attachments"
    quote = relationship("SellerQuote", back_populates="attachments")

# /models/bid_attachment.py (new)
class BidAttachment(Base):
    __tablename__ = "bid_attachments"
    bid = relationship("Bid", back_populates="attachments")
```

#### Services
```python
# /services/seller_quote_service.py
class SellerQuoteService:
    async def submit_quote(quote_data, attachments) -> SellerQuote
    async def convert_to_bid(quote_id: UUID) -> Bid  # Key conversion logic with rollback

# /services/bid_service.py  
class BidService:
    async def list_bids_for_row(row_id: UUID) -> List[Bid]
    async def update_row_bid_count(row_id: UUID)
    async def create_negotiation_thread(bid_id: UUID) -> UUID  # Future negotiation enabler

# /services/file_upload_service.py
class FileUploadService:
    async def upload_quote_attachment(file, quote_id) -> QuoteAttachment
    async def copy_attachments_to_bid(quote_id, bid_id)  # Copy during conversion

# /services/magic_link_service.py
class MagicLinkService:
    def generate_token(row_id: UUID, seller_email: str) -> str
    def validate_token(token: str) -> dict  # Returns row_id, seller_email
```

#### Quote → Bid Conversion Logic with Error Handling
```python
# Transactional conversion with rollback on failure
async def process_quote_submission(quote_data, attachments):
    async with database.transaction():
        try:
            # 1. Create SellerQuote record
            quote = await SellerQuoteService.submit_quote(quote_data, attachments)
            
            # 2. Convert to Bid (this can fail)
            bid = await SellerQuoteService.convert_to_bid(quote.id)
            
            # 3. Copy attachments from quote to bid (this can fail)
            await FileUploadService.copy_attachments_to_bid(quote.id, bid.id)
            
            # 4. Update Row bid_count (this can fail)
            await BidService.update_row_bid_count(quote.row_id)
            
            # 5. Mark quote as converted (final step)
            quote.status = "converted"
            
            return bid
            
        except Exception as e:
            # Transaction automatically rolls back
            # Log error with quote context for debugging
            logger.error(f"Quote conversion failed for quote {quote.id}: {str(e)}")
            # Set quote status to failed for manual review
            quote.status = "failed"
            raise QuoteConversionError(f"Failed to convert quote to bid: {str(e)}")
```

### Frontend Changes

#### Existing Component Extensions
Based on current codebase structure, extend these existing components:

```typescript
// Extend /components/rows/RowDetail.tsx
// Add BidsSection component to show converted bids as tiles
// Reuse existing Row data fetching patterns from useRow hook

// Extend /components/rows/RowCard.tsx  
// Add bid_count display using existing card layout patterns
// Show "X bids received" indicator

// Extend /pages/rows/[id].tsx
// Include bid data in existing Row detail page
// Use existing Clerk auth patterns for buyer protection
```

#### New Pages
```typescript
// /pages/seller-quote/[token].tsx - Quote submission form
// Uses existing design system from components/ui/
// No Clerk auth required but follows existing styling patterns

// /pages/seller-quote/[token]/success.tsx - Conversion confirmation
// Shows "Your quote is now live as a bid" with link to future seller dashboard
```

#### New Components
```typescript
// /components/seller-quote/QuoteForm.tsx
// Follows existing form patterns from components/ui/Form
// Includes FileUploadZone for attachments (images, docs, links)

// /components/seller-quote/ChoiceFactorsRenderer.tsx
// Maps Row.choice_factors JSON to existing UI components:
// Uses components/ui/Select, Input, Textarea consistently

// /components/bids/BidTile.tsx
// New tile component for displaying bids in Row interface
// Shows seller info, price, negotiation_thread_id for future "Start Negotiation" button

// /components/bids/BidsSection.tsx
// Container for bid tiles in Row detail view
// Includes future "Request More Quotes" action button
```

#### File Upload Infrastructure
```typescript
// /services/uploadService.ts
export const uploadQuoteAttachment = async (file: File, quoteToken: string) => {
  // Upload to cloud storage with retry logic
  // Create QuoteAttachment record
  // Return attachment metadata
}

// /hooks/useFileUpload.ts
export const useFileUpload = (quoteToken: string) => {
  // Progress tracking, error handling, file size limits
  // Chunked upload for large files
  // Integrates with quote submission flow
}
```

### Integration Points

#### Row Display Integration
- Extend existing RowDetail component to show bid_count
- Add BidsSection component using existing card grid patterns
- Reuse existing useRow hook for data fetching
- Display bids with seller info, price, attachments using consistent tile design

#### Clerk Auth Integration
- Magic link validation bypasses Clerk for sellers
- Buyer bid viewing uses existing withAuth patterns from pages/rows/[id].tsx
- Consistent UI components between auth and non-auth flows
- Future: sellers can claim bids by creating Clerk accounts

#### Negotiation Workflow Foundation
```typescript
// Future negotiation enablement through bid.negotiation_thread_id
// BidTile component includes "Start Negotiation" button (disabled initially)
// Negotiation threads will reference bid_id for context
// Price amendments create new negotiation_thread entries

// This transforms static bids into negotiable offers:
// 1. Buyer clicks "Start Negotiation" on bid tile
// 2. System creates negotiation_thread, updates bid.negotiation_thread_id  
// 3. Both parties can propose price/term changes
// 4. Final agreement converts to accepted bid
```

#### North Star Metrics Integration
```typescript
// Track quote submission → bid conversion rate (target >95%)
// Measure "negotiable offers from multiple sellers" per Row (target 3+ bids/row)
// Monitor bid engagement: tile views, negotiation thread creation

// Analytics events:
// - quote_submitted (advances procurement search completion)
// - quote_converted_to_bid (creates persistable, negotiable offer)
// - bid_tile_viewed (indicates procurement value)
// - negotiation_started (measures negotiable offer utilization)
```

## Success Criteria
- [ ] Quote form loads with Row.choice_factors rendered correctly
- [ ] File upload works for images, documents, and links with retry logic
- [ ] Quote automatically converts to Bid with full transaction rollback on failure
- [ ] Bids appear as tiles in RowDetail component using existing patterns
- [ ] Row.bid_count updates correctly with database indexes performing well
- [ ] Quote → Bid conversion rate >95% with proper error handling
- [ ] Mobile responsive form works using existing responsive utilities
- [ ] Attachment copying from quote to bid successful
- [ ] Magic link token validation secure with proper indexing
- [ ] Choice factor answers preserved through conversion
- [ ] Negotiation workflow foundation established via negotiation_thread_id

## Dependencies

### Upstream
- **WattData Outreach**: Magic link tokens with expiry handling
- **Cloud Storage**: S3/similar for file attachment infrastructure with chunked uploads
- **SMTP Configuration**: Email notifications for quote received
- **Database Performance**: Proper indexing on high-query columns

### Downstream
- **Row display system**: RowDetail component must render bid tiles from converted quotes
- **Buyer notification system**: Alert Row creators of new bids using existing notification patterns
- **Future seller accounts**: Bid claiming when sellers create Clerk accounts
- **Negotiation system**: Uses negotiation_thread_id for future workflow integration

## North Star Alignment

### Multi-Provider Procurement Search
- Quote intake increases average bids per Row from baseline to target 3+ per active Row
- Choice factor answers improve search relevance matching
- File attachments enable richer procurement decision-making

### Persistable, Negotiable Offers
- Quotes convert to persistent Bid entities with negotiation_thread_id hooks
- Future negotiation workflows enable price/term amendments through thread system
- Attachment preservation supports detailed offer evaluation throughout negotiation
- Bid status tracking enables offer lifecycle management

### Metrics Impact
- **Quote submission rate**: Target 15%+ of magic link recipients submit quotes
- **Multi-provider coverage**: Target 3+ bids per active Row
- **Negotiable offer foundation**: 100% of bids have negotiation_thread_id for future workflow
- **Choice factor completion**: >80% of quotes include all required choice factors

## Risks

### Technical Risks
- **File upload reliability**: Large attachments may fail upload
  - *Mitigation*: Chunked upload, retry logic, file size limits, progress indicators
- **Quote → Bid conversion failures**: Partial conversions leave inconsistent state
  - *Mitigation*: Database transactions, complete rollback, error logging, failed status tracking
- **Database performance**: High query volume on row_id, token lookups
  - *Mitigation*: Comprehensive indexing strategy, query optimization, connection pooling
- **Choice factors schema evolution**: Changes break existing quote forms
  - *Mitigation*: Version choice_factors schema, backward compatibility validation

### Product Risks
- **Complex quote form**: Choice factors + attachments may reduce completion
  - *Mitigation*: Progressive enhancement, optional attachments, mobile-first design
- **Bid tile overload**: Too many bids overwhelm RowDetail interface
  - *Mitigation*: Pagination, filtering, quality scoring integration

### Business Risks
- **Low-quality bids**: Converted quotes may not meet buyer standards
  - *Mitigation*: Bid moderation workflow, seller feedback loop, quality scoring
- **Negotiation workflow complexity**: Future negotiation features may be underutilized
  - *Mitigation*: Simple negotiation UI, guided workflow, buyer education