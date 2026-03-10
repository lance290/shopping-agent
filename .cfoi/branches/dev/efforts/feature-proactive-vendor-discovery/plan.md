<!-- PLAN_APPROVAL: approved by User request via /build-all at 2026-03-10T16:30:00Z -->

# Implementation Plan — BuyAnything Proactive Vendor Discovery

## 0. Alignment Snapshot
- Product North Star: reliable AI-assisted procurement with durable search quality and demand-driven supply growth.
- Effort North Star: extend the existing BuyAnything row search pipeline with strict vendor sufficiency evaluation and live discovery without creating a second UI or polluting canonical vendor data.

## 1. Architecture Fit
- Dispatch seam: `rows_search.py -> SourcingService -> DiscoveryOrchestrator`
- Existing provider/search architecture remains the base for commodity search.
- Vendor discovery path adds DB-first vendor sufficiency scoring before external fan-out.
- SSE/store plumbing remains the existing delivery mechanism.

## 2. Technical Strategy
1. Add discovery persistence models and startup migrations.
2. Add runtime path classifier and discovery mode selector.
3. Add strict coverage scorer for internal vendor candidates.
4. Add discovery adapter interface, basic organic adapter, query planner, extraction, normalization, and dedupe modules.
5. Integrate a `DiscoveryOrchestrator` into `SourcingService`.
6. Route vendor-discovery-path sync and streaming searches through the orchestrator.
7. Persist discovered candidates first, with guarded row-visible bid persistence and no default synchronous canonical vendor creation.
8. Add focused backend tests for pathing, sufficiency, dedupe, and persistence guardrails.

## 3. Risk Controls
- No path-selection logic in more than one place.
- No default synchronous canonical `Vendor` creation for newly discovered vendors.
- No browser-automation dependency in MVP.
- Stable `discovery_session_id` for all discovery sessions.

## 4. Verification
- Targeted backend tests for new discovery modules and row search integration.
- Regression tests for commodity search and same-name same-geo dedupe edge case.
