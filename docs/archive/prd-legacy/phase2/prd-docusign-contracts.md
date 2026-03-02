# PRD: DocuSign Contracts (B2B Closing)

## Business Outcome
- **Measurable impact**: Enable B2B transaction completion → capture high-value deals (tied to North Star: intent-to-close for B2B)
- **Success criteria**: ≥70% of initiated contracts signed within 7 days; 100% of B2B selections above threshold trigger contract flow
- **Target users**: Buyers and sellers completing B2B transactions requiring formal agreements

## Scope
- **In-scope**: 
  - Contract flow trigger on B2B tile selection
  - Contract generation from templates
  - DocuSign envelope creation and sending
  - Signature tracking (sent, viewed, signed)
  - Signed document storage
  - Buyer/seller notifications
- **Out-of-scope**: 
  - Custom contract drafting (templates only)
  - Contract negotiation / redlining
  - Legal review workflow
  - Payment collection within contract (separate from Stripe)
  - Multi-party contracts (beyond buyer + seller)

## User Flow
1. Buyer clicks "Select" on a B2B tile (seller quote or high-value item)
2. System determines contract is required (B2B threshold check)
3. Buyer confirms intent to proceed with contract
4. System generates contract from template with:
   - Buyer info (name, company, email)
   - Seller info (from quote or tile)
   - Item/service details (title, price, description)
   - Standard terms and conditions
5. DocuSign envelope created and sent to both parties
6. Buyer and seller receive signing requests via email
7. Both parties sign (any order)
8. Signed contract stored and linked to bid
9. Both parties notified of completion
10. Bid status updated to "Contracted"

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Contract initiation: authenticated buyer (row owner)
  - Contract signing: buyer + seller (via DocuSign email)
  - Contract viewing: buyer, seller, admins
- **What actions are permitted?** 
  - Buyer: initiate contract, sign, view signed document
  - Seller: sign, view signed document
  - Neither: modify contract (template-based)
- **What data is restricted?** 
  - Contracts contain PII (names, addresses, signatures)
  - Access restricted to parties involved

### Monitoring & Visibility
- **Business metrics**: 
  - Contracts initiated per month
  - Contract completion rate (both signed / initiated)
  - Time to signature (both parties)
  - Contract value distribution
- **Operational visibility**: 
  - DocuSign API error rates
  - Envelope delivery failures
  - Signing abandonment points
- **User behavior tracking**: 
  - Time from initiation to first signature
  - Mobile vs desktop signing

### Billing & Entitlements
- **Monetization**: 
  - Transaction fee on contracted deals (e.g., 2% of contract value)
  - DocuSign costs (per envelope)
- **Entitlement rules**: 
  - Free tier: 3 contracts per month
  - Premium: unlimited (future)
- **Usage limits**: 
  - Max contract value: $1M (for liability reasons)
  - Min contract value: $500 (below this, use Stripe)

### Data Requirements
- **What must persist?** 
  - Contract: bid_id, buyer_id, seller_email, template_id, docusign_envelope_id, status, created_at, signed_at
  - ContractDocument: contract_id, document_url (signed PDF), stored_at
- **Retention**: 7 years (legal requirement for contracts)
- **Relationships**: 
  - Contract → Bid (1:1)
  - Contract → User (buyer)
  - ContractDocument → Contract (1:1)

### Performance Expectations
- **Response time**: Contract generation <5s; Envelope send <10s
- **Throughput**: Support 100 concurrent contract initiations
- **Availability**: 99.9% (business-critical)

### UX & Accessibility
- **Standards**: 
  - Clear contract preview before sending
  - Progress tracker (initiated → sent → buyer signed → seller signed → complete)
  - Mobile-friendly signing (DocuSign handles)
- **Accessibility**: DocuSign's signing UI is WCAG compliant
- **Devices**: Desktop + tablet + mobile

### Privacy, Security & Compliance
- **Regulations**: 
  - eIDAS / ESIGN Act: electronic signatures legally binding
  - GDPR: contracts contain PII; deletion rights apply
  - Industry-specific: may need custom templates for regulated industries
- **Data protection**: 
  - Contracts encrypted at rest
  - Signed documents stored in secure blob storage
  - Access logged for audit
- **Audit trails**: Full envelope history from DocuSign; internal access logs

## Dependencies
- **Upstream**: 
  - Quote Intake (seller info for contract)
  - User authentication (buyer info)
  - Contract templates (legal-approved)
- **Downstream**: 
  - Analytics / reporting
  - Revenue tracking

## Risks & Mitigations
- **Seller doesn't sign** → Reminder emails at 48h, 5 days; buyer notified of delay
- **DocuSign downtime** → Queue contracts for retry; notify users of delay
- **Template doesn't fit use case** → Add "Custom terms" text field; human review for edge cases
- **Legal disputes** → Maintain complete audit trail; store signed originals

## Acceptance Criteria (Business Validation)
- [ ] B2B selection above $1000 triggers contract flow (threshold test)
- [ ] Contract generates with correct buyer/seller/item info (data mapping test)
- [ ] DocuSign envelope sent to both parties within 30s (delivery test)
- [ ] Signed contract stored and accessible to both parties (storage test)
- [ ] Contract completion rate ≥70% within 7 days (industry benchmark: 60-80% for B2B)
- [ ] Bid status updates to "Contracted" after both signatures (state machine test)
- [ ] Contract value and fees tracked for reporting (financial test)
- [ ] Reminder sent at 48h for unsigned contracts (automation test)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (DocuSign API version, template system, storage backend, etc.) are made during /plan and /task phases, not in this PRD.
