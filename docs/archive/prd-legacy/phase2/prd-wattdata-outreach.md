# PRD: WattData Proactive Outreach

## Business Outcome
- **Measurable impact**: Source sellers outside e-commerce APIs → expand marketplace supply (tied to North Star: multi-seller coverage)
- **Success criteria**: ≥20% email open rate; ≥5% quote submission rate from outreach; ≥1 quote received per 10 vendors contacted
- **Target users**: Buyers seeking local services or B2B vendors not on standard platforms

## Scope
- **In-scope**: 
  - Agent queries WattData for vendors matching buyer intent
  - Personalized RFP email generation
  - Email delivery via transactional email service
  - Outreach tracking (sent, opened, clicked, quoted)
  - Magic link generation for quote intake
  - Opt-out / unsubscribe handling
  - Outreach status visible to buyer
- **Out-of-scope**: 
  - SMS outreach (email only for MVP)
  - Phone call automation
  - Seller scoring / ranking by quality
  - Multi-touch drip campaigns (single email + 1 reminder max)

## User Flow
1. Buyer completes RFP (search with extracted intent)
2. Agent determines outreach is appropriate (B2B/local service category)
3. Buyer sees "Finding vendors..." status on row
4. Agent queries WattData for matching vendors
5. Agent generates personalized email for each vendor
6. Emails sent via transactional email service
7. Buyer sees "Outreach sent to X vendors" status
8. Vendor receives email, clicks magic link → Quote Intake flow
9. Buyer notified as quotes arrive
10. After 48h, single reminder sent to non-responders
11. Buyer sees final outreach summary

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Outreach trigger: row owner (buyer) — explicit opt-in or automatic for qualifying categories
  - Outreach status: row owner + collaborators
  - Vendor response: via magic link (no auth required)
- **What actions are permitted?** 
  - Buyer: trigger outreach, view status, pause outreach
  - System: query WattData, send emails, track events
- **What data is restricted?** 
  - Vendor contact info not exposed to buyer (privacy)
  - Buyer contact info not exposed to vendor until quote accepted

### Monitoring & Visibility
- **Business metrics**: 
  - Vendors contacted per row
  - Email delivery rate (delivered / sent)
  - Email open rate
  - Click-through rate (magic link clicks)
  - Quote submission rate
  - Time from email to quote
- **Operational visibility**: 
  - WattData API latency and error rates
  - Email delivery failures by provider/domain
  - Bounce rates
- **User behavior tracking**: 
  - Which vendor categories respond best
  - Optimal send times

### Billing & Entitlements
- **Monetization**: 
  - WattData usage costs (internal)
  - Transaction fee on successful vendor matches (future)
- **Entitlement rules**: 
  - Free tier: 10 vendors per row
  - Premium: 50 vendors per row (future)
- **Usage limits**: 
  - 50 vendors per row per 24h
  - 200 vendors per user per 24h
  - Platform: 10,000 vendors per 24h

### Data Requirements
- **What must persist?** 
  - OutreachEvent: row_id, vendor_email, vendor_name, vendor_source, message_id, sent_at, opened_at, clicked_at, quote_submitted_at, opt_out
  - EmailOptOut: email, opted_out_at, source
- **Retention**: 
  - Outreach events: 1 year
  - Opt-outs: permanent
- **Relationships**: 
  - OutreachEvent → Row (M:1)
  - OutreachEvent → SellerQuote (1:1 optional)

### Performance Expectations
- **Response time**: WattData query <5s; Email batch send <30s for 20 vendors
- **Throughput**: Support 100 concurrent outreach triggers
- **Availability**: 99% (degraded mode: skip outreach if WattData unavailable)

### UX & Accessibility
- **Standards**: 
  - Clear outreach status on row ("Contacting vendors...", "X vendors contacted")
  - Expandable details showing outreach progress
  - No action required from buyer (fully automated)
- **Accessibility**: Status updates announced to screen readers
- **Devices**: Status visible on all devices

### Privacy, Security & Compliance
- **Regulations**: 
  - CAN-SPAM: physical address in email, unsubscribe link, honest subject lines
  - GDPR: vendor can request data deletion; honor opt-outs
  - CASL (Canada): may require prior consent (defer to legal review)
- **Data protection**: 
  - Vendor emails stored encrypted at rest
  - WattData data cached <90 days then purged
- **Audit trails**: Full email send logs for compliance review

## Dependencies
- **Upstream**: 
  - Row + SearchIntent (provides context for outreach)
  - WattData MCP (provides vendor contacts) — **we are investors**
  - Email delivery service (SendGrid/Postmark)
- **Downstream**: 
  - Quote Intake (magic links from outreach)
  - Buyer notifications

## Risks & Mitigations
- **Low vendor response rate** → A/B test subject lines; optimize send times; add phone follow-up (future)
- **Spam complaints** → Strict CAN-SPAM compliance; quality vendor targeting; reputation monitoring
- **WattData rate limits** → Cache query results; batch queries; implement backoff
- **Email deliverability** → Use dedicated sending domain; warm up IP; monitor reputation
- **Wrong vendor matches** → Refine WattData queries; add human review for high-value rows

## Acceptance Criteria (Business Validation)
- [ ] WattData query returns relevant vendors for service-based searches (manual review of 10 queries)
- [ ] Email delivery rate ≥95% (industry standard for transactional email)
- [ ] Email open rate ≥20% (industry benchmark: 15-25% for B2B)
- [ ] Click-through rate ≥5% (industry benchmark: 2-5% for B2B)
- [ ] Quote submission rate ≥5% of clicked (target based on conversion funnel)
- [ ] Unsubscribe link works and is honored within 24h (CAN-SPAM requirement)
- [ ] Outreach status visible to buyer within 5s of send (UX requirement)
- [ ] Reminder email sent at 48h to non-responders (automation test)
- [ ] No outreach to opted-out emails (compliance test)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md
- **Integration Spec**: docs/prd/phase2/wattdata-integration.md

---
**Note:** Technical implementation decisions (email service, caching, queue architecture, etc.) are made during /plan and /task phases, not in this PRD.
