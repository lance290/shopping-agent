# PRD: Buyer Workspace + Tile Provenance

## Business Outcome
- Measurable impact: Reduce buyer comparison fatigue by enabling project-based procurement with explainable tiles (tied to Product North Star: Time to first project row, Time to first offers).
- Target users:
  - Buyers (everyday + power buyers)
  - Collaborators/stakeholders invited via project links

## Scope
- In-scope:
  - Split-pane workspace (chat left, tiles right)
  - Project-based rows (group/indent under a project)
  - Tile interactions: thumbs up/down, select/lock, like, comment, share
  - Like/comment/share available on individual tiles or entire rows
  - Tile detail panel that shows choice-factor highlights and the relevant FAQ/Q&A/chat log that led to the tile
  - Shareable links for collaboration (read/review/select as permitted)
- Out-of-scope:
  - Seller onboarding and seller quote submission
  - Automated vendor outreach
  - Stripe checkout / DocuSign contracts

## User Flow
1. Buyer enters a purchase intent.
2. Agent asks questions to form a structured RFP.
3. Workspace opens with one or more rows of tiles.
4. Buyer clicks a tile to open detail view (FAQ/chat log + choice-factor highlights).
5. Buyer ranks tiles (thumbs) and selects/locks a final option.
6. Buyer can like, comment on, or share any tile or row.
7. Buyer shares project link with a collaborator who can view and participate.

## Business Requirements

### Authentication & Authorization
- Buyer must be authenticated to create and edit projects/rows.
- Collaborators must have access consistent with the shared link policy (view-only vs. can-comment vs. can-select).
- Comments are visible to all collaborators with access to the project.
- Comment visibility must be extensible to support future scopes (e.g., private notes, collaborator-only, buyer-only, seller-visible) without changing the core workspace UX.
- Tile details must not expose sensitive data beyond what’s necessary for explainability.

### Monitoring & Visibility
- Track:
  - Time to first project row
  - Time to first tile detail open
  - % of rows with 1+ tile interactions (thumb/select/like/comment)
  - % of projects shared
  - Likes per tile/row
  - Comments per tile/row
  - Shares per tile/row

### Billing & Entitlements
- No direct billing required for this slice.
- Must support future monetization overlays without changing the core workspace UX.

### Data Requirements
- Persist:
  - Projects, rows, tiles/offers
  - Tile detail provenance data (FAQ/chat log references and choice-factor highlights)
  - Collaboration/share metadata (who shared, permissions, access events)
  - Likes (user, tile/row, timestamp)
  - Comments (user, tile/row, content, timestamp)

### Performance Expectations
- Workspace should open reliably for typical use.
- Tile detail should load without user-visible disruption.

### UX & Accessibility
- Consistent tile UI across categories.
- Tile detail panel must be navigable via keyboard and readable by screen readers.

### Privacy, Security & Compliance
- Treat provenance logs as potentially sensitive.
- Ensure any captured chat/Q&A shown in tile detail follows privacy/redaction rules.

## Dependencies
- Upstream:
  - Product North Star
- Downstream:
  - Multi-channel sourcing
  - Seller quote intake
  - Closing layer

## Risks & Mitigations
- Provenance detail overwhelms users → default to a concise summary with ability to expand.

## Acceptance Criteria (Business Validation)
- [ ] Buyer can create a project row from intent and see tiles (binary).
- [ ] Buyer can open tile detail and see choice-factor highlights + relevant FAQ/chat log (binary).
- [ ] Buyer can thumbs up/down and select/lock a tile (binary).
- [ ] Buyer can like any tile or row (binary).
- [ ] Buyer can comment on any tile or row (binary).
- [ ] Buyer can share any tile or row via link (binary).
- [ ] Buyer can share a project link and collaborator can view the same workspace (binary).
- [ ] Time to first project row ≤ target in Product North Star (source: `.cfoi/branches/main/product-north-star.md`).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
