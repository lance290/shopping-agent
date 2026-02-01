# PRD: Stripe Checkout (Retail Closing)

## Business Outcome
- **Measurable impact**: Enable direct purchases → revenue via affiliate/transaction fees (tied to North Star: intent-to-close conversion)
- **Success criteria**: ≥10% of selected tiles convert to checkout initiation; ≥80% of initiated checkouts complete
- **Target users**: Buyers ready to purchase retail items from search results

## Scope
- **In-scope**: 
  - "Buy Now" button on eligible retail tiles
  - Stripe Checkout Session for external purchases (affiliate links)
  - Payment success tracking
  - Affiliate attribution
  - Basic order confirmation
- **Out-of-scope**: 
  - Stripe Connect (direct payments to sellers)
  - Inventory management
  - Shipping / fulfillment tracking
  - Refund processing (handled by merchant)
  - Multi-item cart

## User Flow
1. Buyer views tiles in a row
2. Buyer clicks "Select" or "Buy Now" on a retail tile
3. If affiliate link: redirect to merchant site with tracking
4. If direct purchase (future): 
   - Checkout modal appears with Stripe Elements
   - Buyer enters payment details
   - Payment processed
   - Confirmation shown
5. Purchase event tracked for analytics and attribution
6. Tile marked as "Purchased" in buyer's row

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Authenticated buyers (row owners only)
- **What actions are permitted?** 
  - Buyer: initiate checkout, complete purchase
  - Collaborators: view-only (cannot purchase)
- **What data is restricted?** 
  - Payment details handled entirely by Stripe (PCI compliance)
  - Purchase history visible only to buyer

### Monitoring & Visibility
- **Business metrics**: 
  - Checkout initiation rate (clicks on Buy Now)
  - Checkout completion rate
  - Average order value
  - Affiliate commission earned
  - Revenue by merchant/provider
- **Operational visibility**: 
  - Stripe API error rates
  - Payment failure reasons
  - Redirect success rate (for affiliate)
- **User behavior tracking**: 
  - Time from search to purchase
  - Drop-off points in checkout funnel

### Billing & Entitlements
- **Monetization**: 
  - Affiliate commissions (2-10% depending on merchant program)
  - Transaction fee on direct purchases (future, ~3%)
- **Entitlement rules**: Checkout available to all authenticated users
- **Usage limits**: None

### Data Requirements
- **What must persist?** 
  - ClickoutEvent: bid_id, user_id, destination_url, affiliate_id, clicked_at
  - PurchaseEvent: bid_id, user_id, amount, currency, stripe_session_id, completed_at
- **Retention**: 7 years (financial records)
- **Relationships**: 
  - ClickoutEvent → Bid (M:1)
  - PurchaseEvent → Bid (M:1)
  - PurchaseEvent → User (M:1)

### Performance Expectations
- **Response time**: Checkout modal load <500ms; Payment processing <5s
- **Throughput**: Support 1000 concurrent checkout sessions
- **Availability**: 99.9% (revenue-critical)

### UX & Accessibility
- **Standards**: 
  - Clear price display before checkout
  - Trust badges (Stripe, secure payment)
  - Mobile-optimized checkout
  - Clear error messages for payment failures
- **Accessibility**: 
  - Stripe Elements are WCAG compliant
  - Error messages announced to screen readers
- **Devices**: Desktop + tablet + mobile

### Privacy, Security & Compliance
- **Regulations**: 
  - PCI DSS: payment data never touches our servers (Stripe handles)
  - Consumer protection: clear pricing, return policy links
- **Data protection**: 
  - No card numbers stored
  - Stripe tokens only
- **Audit trails**: Full transaction logs for financial reporting

## Dependencies
- **Upstream**: 
  - Bid persistence (tile data)
  - User authentication
  - Affiliate program setup with merchants
- **Downstream**: 
  - Analytics / reporting
  - Revenue dashboard (future)

## Risks & Mitigations
- **Cart abandonment** → Streamlined single-item checkout; saved payment methods (future)
- **Affiliate link breakage** → Monitor redirect success; fallback to merchant homepage
- **Stripe downtime** → Graceful error handling; "Try again" option
- **Fraud** → Stripe Radar enabled; velocity checks

## Acceptance Criteria (Business Validation)
- [ ] "Buy Now" button visible on eligible retail tiles (binary test)
- [ ] Affiliate click tracked with correct attribution (tracking test)
- [ ] Stripe Checkout Session creates successfully (integration test)
- [ ] Payment completion recorded in database (persistence test)
- [ ] Checkout completion rate ≥80% of initiated (industry benchmark: 70-85%)
- [ ] Tile status updates to "Purchased" after completion (UX test)
- [ ] Mobile checkout works on iOS Safari and Android Chrome (compatibility test)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (Stripe SDK version, session configuration, etc.) are made during /plan and /task phases, not in this PRD.
