# Product North Star (v2026-01-29)

## Mission
Deliver reliable, transparent, multi-provider procurement search that produces persistable, negotiable offers from multiple sellers and search engines.

## Target Users / Core Jobs
- **Procurement teams & power buyers**: discover, compare, and negotiate offers across multiple sellers.
- **Everyday shoppers**: get relevant results quickly with clear price constraints and provenance.

## Differentiators & Guardrails
- **Structured intent extraction** (LLM + fallback) to capture price/constraints accurately.
- **Provider-specific adapters** so each search engine is queried optimally.
- **Unified normalization** to ensure consistent results across sources.
- **Transparent provider status** (partial results over silence).
- **Persistence-first**: results must survive refresh and repeated searches.
- **No cross-provider dedupe** to preserve negotiation options.

## Success Metrics / OKRs
- **Search success rate**: >90% of searches return results.
- **Price filter accuracy**: >95% of results within requested range.
- **Persistence reliability**: 100% of searches reload with same or enriched results.
- **Provider coverage**: ≥2 providers contributing results per search when configured.
- **Latency**: p95 end-to-end search <= 10–12 seconds with partial results.

## Non‑Negotiables & Exclusions
- API keys and provider credentials **never** exposed to clients.
- No silent failures: always return provider statuses and user-facing messages.
- Preserve raw provider provenance for audit/debug.
- **Exclusions (for now)**: real-time price updates, in-app payments/checkout, sentiment analysis.

## Approver / Date
- **Approver**: Lance
- **Date**: 2026-01-30T04:48:59Z
