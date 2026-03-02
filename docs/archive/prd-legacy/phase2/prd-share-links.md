# PRD: Share Links

## Business Outcome
- **Measurable impact**: Enable viral growth loop → K-factor >1.2 (tied to North Star via user acquisition)
- **Success criteria**: ≥10% of projects shared within 30 days of creation; ≥5% of share recipients convert to new users
- **Target users**: Buyers sharing with team members, stakeholders, or collaborators

## Scope
- **In-scope**: 
  - "Copy Link" button on projects, rows, and individual tiles
  - Shareable URL opens directly to shared item
  - Read-only access for unauthenticated viewers
  - Optional login prompt for full features
  - Share event tracking for attribution
- **Out-of-scope**: 
  - Permission-based sharing (edit access)
  - Password-protected shares
  - Expiring links (all links permanent for MVP)
  - Social media sharing integrations

## User Flow
1. Buyer views their project/row/tile
2. Buyer clicks "Share" or "Copy Link" button
3. System generates shareable URL and copies to clipboard
4. Buyer shares URL via email, Slack, etc. (external)
5. Recipient clicks link
6. Recipient sees shared content in read-only mode
7. Recipient prompted to sign up for full features (like, comment, create own)
8. If recipient signs up, referral attributed to original sharer

## Business Requirements

### Authentication & Authorization
- **Who needs access?** 
  - Share creation: authenticated project/row owners
  - Share viewing: anyone with the link (public read)
- **What actions are permitted?** 
  - Viewers: read-only (view tiles, see likes/comments, no actions)
  - If viewer logs in: becomes collaborator with like/comment permissions
- **What data is restricted?** 
  - Share links expose project/row/bid content publicly
  - User emails and private comments NOT exposed to anonymous viewers

### Monitoring & Visibility
- **Business metrics**: 
  - Share creation rate (shares per project)
  - Share click-through rate
  - Share-to-signup conversion rate
  - Referral attribution (which shares led to new users)
- **Operational visibility**: Link resolution latency, 404 rate for invalid tokens
- **User behavior tracking**: Time on shared page, scroll depth, signup funnel

### Billing & Entitlements
- **Monetization**: None directly (growth feature)
- **Entitlement rules**: Share creation available to all authenticated users
- **Usage limits**: 
  - Max 100 share links per project (prevent abuse)
  - No rate limit on share viewing

### Data Requirements
- **What must persist?** 
  - Share link: token, resource_type, resource_id, created_by, created_at, access_count
  - Referral attribution: share_token → new_user_id
- **Retention**: Permanent (shares don't expire in MVP)
- **Relationships**: 
  - ShareLink → Project/Row/Bid (polymorphic)
  - ShareLink → User (creator)
  - User → ShareLink (referral source)

### Performance Expectations
- **Response time**: Link generation <200ms; Link resolution <300ms
- **Throughput**: Support viral spikes (1000 concurrent viewers on popular share)
- **Availability**: 99.9% — shares are public-facing

### UX & Accessibility
- **Standards**: 
  - "Link copied!" toast confirmation
  - Share icon consistent with platform (e.g., share-2 from Lucide)
  - Read-only badge visible to viewers
- **Accessibility**: 
  - Copy button keyboard accessible
  - Success confirmation announced to screen readers
- **Devices**: Desktop + tablet + mobile (shares must render well on all)

### Privacy, Security & Compliance
- **Regulations**: 
  - Shared content becomes semi-public; user must consent to sharing
  - GDPR: user can delete shares (and content becomes inaccessible)
- **Data protection**: 
  - Tokens are unguessable (256-bit random)
  - No sensitive data in URL (token only, no user IDs)
- **Audit trails**: Log share creation and access for analytics

## Dependencies
- **Upstream**: 
  - Project/Row/Bid persistence (complete)
  - User authentication (for share creation)
- **Downstream**: 
  - Viral coefficient measurement
  - Collaborator invitations (future: upgrade share to edit access)

## Risks & Mitigations
- **Unintended data exposure** → Clear UI warning before sharing; "Public link" label
- **Link abuse / scraping** → Rate limit views per IP; add CAPTCHA if suspicious
- **Orphaned shares** → Clean up when source resource deleted

## Acceptance Criteria (Business Validation)
- [ ] Copy Link works for project, row, and tile (3 resource types tested)
- [ ] Shared link resolves to correct content (100% accuracy)
- [ ] Anonymous viewer can see tiles but NOT like/comment/select (authorization test)
- [ ] Share creation latency ≤200ms (standard for UI action)
- [ ] Share access_count increments on each view (tracking works)
- [ ] New user signup attributes referral to share_token (attribution test)
- [ ] ≥5% share-to-signup conversion (baseline: 0%, industry benchmark: 2-10% for viral features)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (token generation, URL structure, caching, etc.) are made during /plan and /task phases, not in this PRD.
