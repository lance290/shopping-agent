# PRD: Seller Quote Intake

## Business Outcome
- **Measurable impact**: Open seller side of marketplace → enable reverse-auction dynamics (tied to North Star: multi-seller negotiation)
- **Success criteria**: ≥20% of outreach recipients submit a quote; ≥50% of submitted quotes contain all required fields
- **Target users**: Service providers, B2B vendors, local businesses responding to buyer RFPs

## Scope
- **In-scope**: 
  - Magic link delivery to sellers (via outreach email)
  - No-account-required quote submission form
  - Choice factor questions derived from buyer's search intent
  - Price, description, attachments input
  - Quote → Bid conversion (appears as tile)
  - Buyer notification on new quote
- **Out-of-scope**: 
  - Seller dashboard / portal
  - Quote editing after submission (v1 is one-shot)
  - Real-time negotiation / chat with buyer
  - Seller account management

## User Flow
1. Seller receives outreach email with RFP summary
2. Seller clicks magic link in email
3. Quote form loads with:
   - Buyer's need summary (read-only)
   - Choice factor questions to answer
   - Price input with type selector (fixed/hourly/negotiable)
   - Description textarea
   - Attachment uploader (images, docs, links)
   - Seller contact info (pre-filled from outreach data)
4. Seller fills form and submits
5. System validates inputs
6. Quote converted to Bid, appears in buyer's row
7. Buyer receives notification of new quote
8. (Optional) Seller prompted to create account for future opportunities

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Quote submission: anyone with valid magic link token
  - Quote viewing: seller (own quotes), buyer (quotes in their rows)
- **What actions are permitted?** 
  - Seller: submit quote, view own submission
  - Buyer: view quotes, accept/reject
- **What data is restricted?** 
  - Seller contact info visible only to buyer (not other sellers)
  - Buyer contact info hidden from seller until accepted

### Monitoring & Visibility
- **Business metrics**: 
  - Quote submission rate (% of magic links that convert)
  - Quote completeness (% with all fields filled)
  - Time from email open to submission
  - Quote acceptance rate
- **Operational visibility**: Form validation errors, submission failures
- **User behavior tracking**: Form field completion order, abandonment points

### Billing & Entitlements
- **Monetization**: Transaction fee on accepted quotes (future)
- **Entitlement rules**: Quote submission free for all sellers
- **Usage limits**: 
  - 1 quote per seller per row (prevent spam)
  - Max 10 attachments per quote

### Data Requirements
- **What must persist?** 
  - SellerQuote: token, row_id, seller_email, seller_name, seller_company, price, description, answers, attachments, status, timestamps
  - QuoteAttachment: quote_id, type, url, filename
- **Retention**: 2 years (for dispute resolution)
- **Relationships**: 
  - SellerQuote → Row (M:1)
  - SellerQuote → Bid (1:1 after conversion)
  - QuoteAttachment → SellerQuote (M:1)

### Performance Expectations
- **Response time**: Form load <500ms; Submission <2s (includes file uploads)
- **Throughput**: Support 100 concurrent quote submissions
- **Availability**: 99.9% — seller-facing, critical for conversion

### UX & Accessibility
- **Standards**: 
  - Clean, professional form design (sellers are businesses)
  - Progress indicator for multi-step or long forms
  - Clear error messages with field highlighting
  - Mobile-friendly (sellers may respond on phone)
- **Accessibility**: 
  - Form labels properly associated
  - Error messages announced to screen readers
  - Keyboard navigation for all inputs
- **Devices**: Desktop + tablet + mobile (mobile critical)

### Privacy, Security & Compliance
- **Regulations**: 
  - Seller provides business data; include privacy notice
  - GDPR: seller can request quote deletion
- **Data protection**: 
  - Magic link tokens single-use for submission (can be reused for viewing)
  - File uploads scanned for malware
  - Input sanitized for XSS/injection
- **Audit trails**: Log quote submissions with IP, timestamp

## Dependencies
- **Upstream**: 
  - WattData Outreach (provides magic link tokens and seller context)
  - Row/SearchIntent (provides choice factors for questions)
- **Downstream**: 
  - Buyer notification system
  - Bid display (quotes appear as tiles)

## Risks & Mitigations
- **Low form completion rate** → Progressive disclosure; save draft; minimal required fields
- **Spam quotes** → Rate limit per IP; CAPTCHA on suspicious patterns
- **Invalid/fake submissions** → Manual review queue for first-time sellers
- **File upload abuse** → Size limits (10MB), type restrictions, virus scanning

## Acceptance Criteria (Business Validation)
- [ ] Magic link resolves to pre-filled quote form (token validation works)
- [ ] Quote submission with all required fields succeeds (happy path)
- [ ] Quote appears as tile in buyer's row within 5s of submission
- [ ] Buyer receives notification of new quote (email or in-app)
- [ ] ≥50% of submitted quotes have all required fields (form UX quality)
- [ ] Quote submission latency ≤2s p95 (acceptable for form submit)
- [ ] Seller cannot submit multiple quotes to same row (dedup works)
- [ ] Form accessible via keyboard only (accessibility test)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (form framework, file storage, etc.) are made during /plan and /task phases, not in this PRD.
