# PRD: Email Handoff (MVP Closing)

## Business Outcome
- **Measurable impact**: Enable transaction completion without heavy infrastructure → faster path to revenue (tied to North Star: intent-to-close rate)
- **Success criteria**: ≥30% of selected quotes result in completed transaction; ≥80% of handoff emails opened by both parties
- **Target users**: Buyers selecting service quotes (HVAC, roofing, private jets, etc.)

## Scope
- **In-scope**: 
  - Buyer "Select" action on seller quote triggers handoff
  - Introduction email to both buyer and seller
  - Contact info exchange (with consent)
  - Deal summary with choice factors and agreed terms
  - "Mark as Closed" action for buyer (tracking)
  - Basic transaction tracking (selected → introduced → closed)
- **Out-of-scope**: 
  - Payment processing (use Stripe for retail)
  - Contract generation (use DocuSign for B2B contracts)
  - Escrow or payment protection
  - Dispute resolution
  - In-app messaging/chat

## User Flow
1. Buyer reviews seller quotes in their row
2. Buyer clicks "Select" on preferred quote
3. Confirmation modal: "This will introduce you to [Seller] via email. Continue?"
4. Buyer confirms → System sends introduction emails
5. **Email to Buyer**: Seller contact info, quote summary, next steps
6. **Email to Seller**: Buyer contact info, deal summary, "quote accepted" notification
7. Parties communicate directly (email/phone) to finalize
8. Buyer returns to app and clicks "Mark as Closed" (optional)
9. System tracks conversion for metrics

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Select action: row owner (buyer) only
  - Mark as closed: row owner only
- **What actions are permitted?** 
  - Buyer: select quote, trigger handoff, mark closed
  - Seller: receives notification (no action required in-app)
- **What data is restricted?** 
  - Buyer contact info shared with seller ONLY after selection
  - Seller contact info shared with buyer ONLY after selection

### Monitoring & Visibility
- **Business metrics**: 
  - Selection rate (% of quotes that get selected)
  - Handoff completion rate (emails delivered to both)
  - Close rate (% of handoffs marked as closed)
  - Time from selection to close
- **Operational visibility**: Email delivery failures, bounce rates
- **User behavior tracking**: Time spent reviewing quotes before selection

### Billing & Entitlements
- **Monetization**: 
  - Transaction fee on closed deals (future, requires payment integration)
  - For MVP: track value for reporting only
- **Entitlement rules**: Unlimited selections for all users (MVP)
- **Usage limits**: None for MVP

### Data Requirements
- **What must persist?** 
  - DealHandoff: row_id, quote_id, buyer_email_sent_at, seller_email_sent_at, buyer_opened_at, seller_opened_at, closed_at, deal_value
- **Retention**: 2 years (for metrics and potential disputes)
- **Relationships**: 
  - DealHandoff → Row (M:1)
  - DealHandoff → SellerQuote (1:1)

### Performance Expectations
- **Response time**: Selection action <1s; Emails sent within 30s
- **Throughput**: Support 50 concurrent selections
- **Availability**: 99% (degraded mode: queue emails if delivery service down)

### UX & Accessibility
- **Standards**: 
  - Clear confirmation before sharing contact info
  - Success state shows "Introduction sent" with next steps
  - Email templates professional and mobile-friendly
- **Accessibility**: Confirmation modal keyboard accessible
- **Devices**: Works on all devices

### Privacy, Security & Compliance
- **Regulations**: 
  - Explicit consent before sharing contact info (modal confirmation)
  - GDPR: users can request deletion of handoff records
- **Data protection**: 
  - Contact info encrypted at rest
  - Emails sent via authenticated SMTP
- **Audit trails**: Log all handoff events with timestamps

## Email Templates

### Buyer Introduction Email
```
Subject: Your quote from [Seller Company] for [Request Summary]

Hi [Buyer Name],

Great news! You've selected [Seller Company] for your [Request Summary].

Here's how to proceed:

📋 **Quote Summary**
- Price: [Price]
- [Choice Factor 1]: [Value]
- [Choice Factor 2]: [Value]

📞 **Seller Contact**
- Name: [Seller Name]
- Company: [Seller Company]
- Email: [Seller Email]
- Phone: [Seller Phone]

**Next Steps**
1. Reach out to [Seller Name] to finalize details
2. Agree on timeline and payment terms
3. Once complete, mark as closed in [App Name] to help us improve

Questions? Reply to this email.

—[App Name] Team
```

### Seller Notification Email
```
Subject: 🎉 Your quote was accepted! [Request Summary]

Hi [Seller Name],

[Buyer Name] has accepted your quote for [Request Summary].

📋 **Deal Summary**
- Your Price: [Price]
- Request: [Request Summary]
- [Choice Factor 1]: [Value]

📞 **Buyer Contact**
- Name: [Buyer Name]
- Email: [Buyer Email]
- Phone: [Buyer Phone] (if provided)

**Next Steps**
Reach out to [Buyer Name] within 24 hours to finalize the deal.

Congrats on winning this opportunity!

—[App Name] Team
```

## Dependencies
- **Upstream**: 
  - Seller Quote Intake (provides quotes to select)
  - Row/SearchIntent (provides deal context)
  - Email delivery service (SendGrid/Postmark)
- **Downstream**: 
  - Transaction tracking/reporting
  - Future: Stripe/DocuSign for formalized closing

## Risks & Mitigations
- **Low close rate** → Follow-up email at 48h asking if deal completed; add incentive to mark closed
- **Contact info abuse** → Rate limit selections; report/block bad actors
- **Email deliverability** → Use transactional email service; monitor bounces
- **Buyer/seller don't connect** → Include phone numbers when available; reminder emails

## Acceptance Criteria (Business Validation)
- [ ] Buyer can select a quote and see confirmation modal
- [ ] Introduction emails sent to both parties within 30s
- [ ] Emails contain correct contact info and deal summary
- [ ] Buyer can mark deal as "closed" in UI
- [ ] Selection and close events tracked for metrics
- [ ] ≥80% email delivery rate (industry standard)
- [ ] Contact info NOT shared before explicit selection

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md
- **Related**: prd-quote-intake.md, prd-docusign-contracts.md

---
**Note:** This is the MVP closing mechanism. For transactions requiring contracts or payment protection, escalate to DocuSign (B2B) or Stripe (retail) flows.
