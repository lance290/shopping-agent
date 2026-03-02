# Phase 2 Execution Order

**Created:** 2026-01-31  
**Last Updated:** 2026-02-03

---

## Dependency Graph

```
                    ┌─────────────────────┐
                    │   Search Arch v2    │
                    │   ✅ COMPLETE       │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Tile Provenance  │ │ Likes & Comments │ │   Share Links    │
│      (P0-1)      │ │      (P0-2)      │ │      (P0-3)      │
│   Independent    │ │   Independent    │ │   Independent    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
           ▼                                     ▼
┌──────────────────┐                  ┌──────────────────┐
│ Merchant Registry│                  │ WattData Outreach│
│      (P1-4)      │                  │      (P1-5)      │
│   Independent    │                  │  Needs: Tile UX  │
└────────┬─────────┘                  └────────┬─────────┘
         │                                     │
         └─────────────────┬───────────────────┘
                           │
                           ▼
                ┌──────────────────┐
                │   Quote Intake   │
                │      (P1-6)      │
                │ Needs: Merchants │
                │   + Outreach     │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  Email Handoff   │
                │     (P1-7)       │
                │ Needs: Quote     │
                └────────┬─────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│ Stripe Checkout  │          │DocuSign Contracts│
│      (P2-8)      │          │      (P2-9)      │
│   Independent    │          │ Needs: Handoff   │
└──────────────────┘          └──────────────────┘
```

---

## Execution Waves

### Wave 1: Buyer Engagement (P0) — Can Start Immediately
All three are independent; can be developed in parallel.

| Order | PRD | Effort | Est. Effort | Dependencies | Exit Criteria |
|:-----:|-----|--------|-------------|--------------|---------------|
| 1 | prd-tile-provenance.md | S | 2-3 days | None | Buyer can click tile, see provenance |
| 2 | prd-likes-comments.md | S | 2-3 days | None | Likes/comments persist across reload |
| 3 | prd-share-links.md | S | 2-3 days | None | Copy link works, share resolves |

**Wave 1 Total:** ~1 week (parallel) or ~1.5 weeks (sequential)

**Milestone:** Buyer-side experience complete. Users can search, explore, engage, and share.

---

### Wave 2: Seller Loop (P1) — Requires Wave 1 Complete

| Order | PRD | Effort | Est. Effort | Dependencies | Exit Criteria |
|:-----:|-----|--------|-------------|--------------|---------------|
| 4 | prd-merchant-registry.md | M | 1 week | Wave 1 (tiles exist) | Merchants can register, receive RFP notifications |
| 5 | prd-wattdata-outreach.md | M | 1 week | Wave 1 (tiles exist) | Agent queries WattData, sends emails |
| 6 | prd-quote-intake.md | M | 1 week | #4, #5 (merchants + outreach) | Seller submits quote via magic link |
| 7 | prd-email-handoff.md | S | 3-4 days | #6 (quotes to select) | Buyer selects quote, email intro sent |

**Wave 2 Total:** ~3-3.5 weeks (with parallelization: #4 and #5 can run together)

**Milestone:** Two-sided marketplace operational. Sellers can respond to buyer RFPs. MVP closing via email.

---

### Wave 3: Formal Closing Layer (P2) — Requires Wave 2 Complete

| Order | PRD | Effort | Est. Effort | Dependencies | Exit Criteria |
|:-----:|-----|--------|-------------|--------------|---------------|
| 8 | prd-stripe-checkout.md | M | 1 week | None (retail tiles exist from Phase 1) | Affiliate clicks tracked; checkout works |
| 9 | prd-docusign-contracts.md | L | 1.5 weeks | #7 (email handoff as baseline) | B2B selection triggers contract flow |

**Wave 3 Total:** ~2.5 weeks

**Milestone:** Full transaction lifecycle complete. Formal payment + contracts enabled.

**Note:** Email Handoff (Wave 2) provides MVP closing. Wave 3 adds formal payment processing and contract signing for higher-value transactions.

---

## Critical Path

The longest dependency chain determines minimum time to full completion:

```
Search Arch v2 (✅) 
    → Tile Provenance (2-3d) 
    → Merchant Registry (1w) [parallel with WattData]
    → Quote Intake (1w) 
    → Email Handoff (3-4d)
    → DocuSign Contracts (1.5w)

Critical Path Total: ~5 weeks
```

**Parallelization opportunities:**
- Wave 1 items (1, 2, 3) can all run in parallel
- Merchant Registry (#4) and WattData Outreach (#5) can run in parallel
- Stripe Checkout (#8) can run in parallel with DocuSign (#9)
- Email Handoff (#7) is quick (S) and unblocks revenue before Wave 3

**Realistic timeline with parallelization:** ~4.5 weeks

**Key insight:** Email Handoff enables MVP transactions by end of Week 3, before Stripe/DocuSign are complete.

---

## Recommended Execution Sequence

### Week 1
| Day | Focus | PRDs |
|-----|-------|------|
| Mon-Tue | Tile provenance backend + frontend | #1 |
| Wed-Thu | Likes/comments click-test + fixes | #2 |
| Fri | Share links implementation | #3 |

### Week 2 (Parallel tracks)
| Day | Track A | Track B |
|-----|---------|----------|
| Mon-Wed | Merchant Registry: DB + registration flow | WattData MCP integration |
| Thu-Fri | Merchant Registry: dashboard + matching | Email templates + SendGrid setup |

### Week 3
| Day | Focus | PRDs |
|-----|-------|------|
| Mon-Wed | Quote intake form + magic links | #6 |
| Thu-Fri | Quote → Bid conversion + notifications | #6 |

### Week 4
| Day | Focus | PRDs |
|-----|-------|------|
| Mon-Tue | Email Handoff: selection + intro emails | #7 |
| Wed | Email Handoff: mark closed + tracking | #7 |
| Thu-Fri | Stripe checkout integration | #8 |

### Week 5 (if needed)
| Day | Focus | PRDs |
|-----|-------|------|
| Mon-Fri | DocuSign contract flow | #9 |

---

## Risk-Adjusted Order

If external dependencies (WattData, Stripe, DocuSign) have long setup times:

1. **Start API key acquisition NOW** for:
   - WattData (we're investors — should be fast)
   - Stripe (likely already have)
   - DocuSign (may take 1-2 weeks for sandbox)
   - SendGrid/Postmark (1-2 days)

2. **If DocuSign delayed**, reorder:
   - Move Stripe Checkout (#6) earlier
   - Run DocuSign (#7) last when API ready

3. **If WattData delayed**:
   - Implement Quote Intake (#5) with manual magic link generation
   - Add WattData automation when ready

---

## Status Tracker

| PRD | Status | Started | Completed | Blockers |
|-----|--------|---------|-----------|----------|
| prd-tile-provenance.md | ✅ Complete | 2026-02-06 | 2026-02-06 | - |
| prd-likes-comments.md | 🔲 Not Started | - | - | - |
| prd-share-links.md | 🔲 Not Started | - | - | - |
| prd-merchant-registry.md | 🔲 Not Started | - | - | - |
| prd-wattdata-outreach.md | 🔲 Not Started | - | - | - |
| prd-quote-intake.md | 🔲 Not Started | - | - | - |
| prd-email-handoff.md | 🔲 Not Started | - | - | - |
| prd-stripe-checkout.md | 🔲 Not Started | - | - | - |
| prd-docusign-contracts.md | 🔲 Not Started | - | - | - |

**Legend:** 🔲 Not Started | 🟡 In Progress | ✅ Complete | 🔴 Blocked

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-31 | Wave 1 all P0, parallel | Independent features, maximize velocity |
| 2026-01-31 | Quote Intake depends on Outreach | Magic links generated during outreach |
| 2026-01-31 | DocuSign last | Longest external dependency, B2B can wait |
| 2026-02-01 | Add Merchant Registry (P1) | Favor registered merchants over cold outreach; build defensible network |
| 2026-02-01 | Add Email Handoff (P1) | MVP closing mechanism before Stripe/DocuSign; enables revenue faster |
| 2026-02-01 | Email Handoff before Wave 3 | Quick win (S effort) that unblocks transactions |
| 2026-02-03 | Phase 2 = PartFinder parity | Competitive analysis shows Phase 2 delivers their core RFQ features |
| 2026-02-03 | Merchant Registry is key differentiator | Two-sided marketplace vs their cold-outreach-only model |
| 2026-02-03 | WattData partnership is strategic | We're investors — preferred access, input on roadmap |
| 2026-02-03 | B2B ready after Phase 2 | Service taxonomy + merchant registry = enterprise-capable |
| 2026-02-03 | Defer ERP/photo search to Phase 3 | Not needed for B2B services; only for industrial parts vertical |

---

## Competitive Context

Phase 2 delivers **feature parity with PartFinder** (B2B industrial parts sourcing startup):

| PartFinder Feature | Our Phase 2 Equivalent |
|-------------------|------------------------|
| AI Email Agent | WattData Outreach + SendGrid |
| RFQ to suppliers | `POST /rows/{row_id}/outreach` |
| Quote submission | Magic link intake |
| Response tracking | `outreach_events` table |
| Deal closing | Email Handoff + DocuSign |

**We have features they don't:**
- Merchant Registry (two-sided marketplace)
- Service provider network with taxonomy
- Social features (likes, comments)
- Viral sharing mechanics
- Consumer marketplace integrations (Amazon, Google Shopping)

**Remaining gaps after Phase 2 (Phase 3+):**
- ERP integrations (SAP/NetSuite)
- Parts-specific AI training
- Photo-based search
- Automated negotiation

See [Competitive Analysis](../Competitive_Analysis_PartFinder.md) for full details.
