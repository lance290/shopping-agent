# Product North Star (v2026-02-06 — Phase 4)

## Mission
Enable anyone to **buy anything** — from everyday goods to B2B services — through an AI-agent facilitated marketplace that sources competitive offers, connects buyers with sellers, and **generates platform revenue** on every transaction.

## Target Users / Core Jobs
- **Buyers (B2C)**: search for products, get ranked results from multiple providers, click out or buy directly.
- **Buyers (B2B)**: describe complex procurement needs conversationally, receive structured RFPs and vendor quotes.
- **Sellers/Vendors**: discover buyer needs, submit quotes, close deals through the platform.
- **Platform operator (you)**: earn revenue on every affiliate clickout, marketplace transaction, and B2B deal.

## Differentiators & Guardrails
- **Structured intent extraction** (LLM + fallback) to capture price/constraints accurately.
- **Provider-specific adapters** so each search engine is queried optimally.
- **Unified normalization** to ensure consistent results across sources.
- **Transparent provider status** (partial results over silence).
- **Persistence-first**: results must survive refresh and repeated searches.
- **No cross-provider dedupe** to preserve negotiation options.
- **Two-sided marketplace**: buyers post needs, sellers compete with offers.
- **Revenue capture on every flow**: affiliate tags on clickouts, Stripe Connect fees on direct transactions.
- **Tile provenance**: every result explains why it was recommended.

## Success Metrics / OKRs
- **Search success rate**: >90% of searches return results.
- **Price filter accuracy**: >95% of results within requested range.
- **Persistence reliability**: 100% of searches reload with same or enriched results.
- **Provider coverage**: ≥2 providers contributing results per search when configured.
- **Latency**: p95 end-to-end search <= 10–12 seconds with partial results.
- **Revenue per search**: >0 (at minimum, affiliate tags on every clickout).
- **Seller response rate**: >20% of outreached vendors respond with quotes.
- **Intent-to-close rate**: >5% of searches result in a purchase or contract.

## Non‑Negotiables & Exclusions
- API keys and provider credentials **never** exposed to clients.
- No silent failures: always return provider statuses and user-facing messages.
- Preserve raw provider provenance for audit/debug.
- **Platform must earn on every monetizable action** — no transaction should bypass revenue capture.
- **Exclusions (for now)**: real-time price updates, sentiment analysis, premium seller tiers.

## Approver / Date
- **Approver**: Lance
- **Date**: 2026-02-06
