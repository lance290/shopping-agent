# PRD: Multi-Channel Sourcing + Proactive Outreach

## Business Outcome
- Measurable impact: Provide buyers with a competitive set of real offers quickly (tied to Product North Star: Time to first offers; offers/bids per row).
- Target users:
  - Buyers needing both e-commerce and local/B2B options

## Scope
- In-scope:
  - Multi-channel sourcing strategy that can produce “instant offers” for standardized goods/services
  - Proactive outreach for vendors not available through standard connectors
  - Outreach tracking (sent, delivered, responded, no response)
  - Vendor response intake sufficient to surface as a tile (even if seller UI is separate)
- Out-of-scope:
  - Full seller-side portal UI
  - Stripe checkout / DocuSign contracts

## User Flow
1. Buyer completes an RFP in chat.
2. System retrieves instant offers from available sourcing channels.
3. Agent identifies missing coverage and initiates outreach to additional vendors.
4. Vendors respond via an allowed channel.
5. Vendor responses are captured and can be displayed as tiles in the buyer row.

## Business Requirements

### Authentication & Authorization
- Only authenticated buyers can trigger outreach tied to their projects.
- Vendor contact details and outreach transcripts must be access-controlled.

### Monitoring & Visibility
- Track:
  - Time to first offers
  - Offers/bids per row
  - Outreach volume per row
  - Vendor response rate
  - Median time to first vendor response

### Billing & Entitlements
- No direct buyer billing required for sourcing/outreach.
- Must support future entitlements (e.g., outreach limits, premium sourcing).

### Data Requirements
- Persist:
  - Sourcing results with provenance
  - Outreach attempts (who, when, channel, template version)
  - Vendor responses and mapping to buyer rows

### Performance Expectations
- Initial offers should appear quickly for common categories.
- Outreach should not block buyer interaction with the workspace.

### UX & Accessibility
- Buyer should clearly understand which tiles are instant offers vs. vendor-provided quotes.
- Clear status indicators for “outreach in progress / awaiting response”.

### Privacy, Security & Compliance
- Vendor contact info is sensitive.
- Outreach content must avoid leaking buyer PII unnecessarily.

## Dependencies
- Upstream:
  - Buyer workspace + tile provenance
- Downstream:
  - Seller quote intake (if seller UI is introduced)
  - Closing layer

## Risks & Mitigations
- Low vendor response rate → provide timeouts, escalation, and alternative suggestions.

## Acceptance Criteria (Business Validation)
- [ ] Buyer sees at least one instant offer tile when an eligible channel exists (binary).
- [ ] Agent can initiate outreach to a vendor and record an outreach event (binary).
- [ ] A vendor response can be ingested and displayed as a buyer tile (binary).
- [ ] Offers/bids per row can reach the Product North Star target when sufficient channels/vendors exist (source: `.cfoi/branches/main/product-north-star.md`).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
