# PRD: Unified Closing Layer (Stripe + DocuSign)

## Business Outcome
- Measurable impact: Increase “intent-to-close” completion by allowing retail payment and B2B contract execution to occur in a single consistent flow.
- Target users:
  - Buyers selecting a final tile
  - Sellers closing a deal (especially B2B)

## Scope
- In-scope:
  - Retail closing flow via a checkout experience
  - B2B closing flow where a “contract required” selection triggers a DocuSign signing workflow
  - C2C closing supported only when it fits the same checkout pattern (non-escrow), with clear buyer/seller acknowledgement
  - Multi-vendor project: support closing more than one selected tile in a project
  - Status visibility: buyer can see whether a selected tile is pending payment/contract/completed
- Out-of-scope:
  - Proprietary fulfillment/logistics
  - Full invoicing/ERP replacement
  - Escrow, chargeback arbitration, dispute resolution workflows, and marketplace trust/safety tooling beyond basic audit logs

## User Flow
1. Buyer selects/locks a tile.
2. System identifies whether the selection is retail checkout or contract-required.
3. Retail: buyer completes payment.
4. B2B: system initiates contract signing for both parties.
5. System marks the selection as closed and updates the project view.

## Business Requirements

### Authentication & Authorization
- Only the buyer (and authorized collaborators) can initiate closing.
- Only the buyer and the relevant seller can access contract documents.

### Monitoring & Visibility
- Track:
  - Intent-to-close conversion rate
  - Payment success rate
  - Contract completion rate
  - Time to close (payment/contract)

### Billing & Entitlements
- Retail: supports affiliate model and/or direct transaction processing per business policy.
- B2B: supports transaction fees per business policy.

### Data Requirements
- Persist:
  - Closing state per selected tile
  - Payment/contract references (identifiers and status)
  - Audit logs for signing and payment events

### Performance Expectations
- Closing flow should be reliable and provide clear recovery paths.

### UX & Accessibility
- Buyer-facing closing UX must be consistent across retail and B2B.
- Status must be visible in the project/row UI.

### Privacy, Security & Compliance
- Payment and contract flows must meet provider security expectations.
- Audit trails must exist for compliance and dispute resolution.

## Dependencies
- Upstream:
  - Buyer workspace + tile provenance
  - Seller quote intake (for B2B)
- Downstream:
  - Growth/analytics and optimization

## Risks & Mitigations
- Contract/payment failures create trust issues → clear status + retries + support escalation.

## Acceptance Criteria (Business Validation)
- [ ] Buyer can complete a retail close for a selected tile (binary).
- [ ] Buyer can trigger a contract-required close and both parties can complete signing (binary).
- [ ] Project view reflects closing status per selected tile (binary).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
