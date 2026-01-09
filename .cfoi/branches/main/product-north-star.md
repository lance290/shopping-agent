# Product North Star (v2026-01-08)

## Mission
Eliminate the friction of comparison shopping by providing an AI agent that transforms natural-language requests into a competitive procurement board—sourcing sellers, collecting bids, and presenting normalized offers so buyers can make confident purchasing decisions in minutes, not hours.

## Target Users & Core Jobs

### Primary: Everyday Buyer
- **Job**: Find the best deal without researching across multiple sites
- **Pain**: Opening 10 tabs, comparing inconsistent pricing, missing hidden costs

### Secondary: Power Buyer  
- **Job**: Set constraints, control vendor quality, run negotiation rounds
- **Pain**: Manual vendor outreach, no structured comparison, time-consuming RFQs

### Tertiary: Seller/Vendor
- **Job**: Get qualified leads, easy quoting, clear path to closing
- **Pain**: Cold outreach, unclear buyer requirements, lost deals

## Differentiators

1. **Chat-native procurement**: One conversation creates structured, actionable requests
2. **Agent-driven sourcing**: AI finds, invites, and manages sellers automatically  
3. **Normalized comparison**: Apples-to-apples view of price + shipping + ETA + policies
4. **Competitive by default**: Target ≥3 comparable bids per request
5. **Transparency**: Full audit trail of agent actions and bid provenance

## Success Metrics / OKRs

| Metric | Target | Rationale |
|--------|--------|-----------|
| Time to first request | <15 seconds | Frictionless entry |
| Bids per row | ≥3 | Competitive marketplace |
| Time to first bid | <5 minutes | Fast value delivery |
| Conversion rate (rows closed) | >20% | Buyer finds value |
| Buyer satisfaction (thumbs up) | >80% | Quality matches |

## Non-Negotiables

1. **Every bid must be real**: No invented offers—each tile maps to actual seller submission or verified feed
2. **User confirms purchases**: No autonomous buying without explicit approval
3. **Price transparency**: Total cost (item + shipping + tax) always visible
4. **Audit trail**: Every agent action is logged and visible to the user
5. **Zustand as source of truth**: Frontend state management is centralized and consistent

## Exclusions (Out of Scope)

- General web-scraping engine (prefer APIs, feeds, seller onboarding)
- "Any product instantly" (focus on categories with accessible sellers)
- Fully autonomous purchasing
- Payment processing in MVP (handoff model first)

## Approver / Date
- **Reverse-engineered from**: `agent-facilitated-competitive-bidding-prd.md`
- **Date**: 2026-01-08
- **Status**: Draft - Awaiting human approval
