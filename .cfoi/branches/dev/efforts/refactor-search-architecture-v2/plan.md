<!-- PLAN_APPROVAL: approved by Lance at 2026-01-30T05:04:20Z -->

# Implementation Plan — Search Architecture v2 (Refactor)

## 0. Alignment Snapshot
- **Product North Star (v2026-01-29)**: Reliable, transparent multi-provider procurement search with structured intent extraction, provider-specific adapters, normalized persistence, and no silent failures. Approved by Lance @ 2026-01-30T04:48:59Z.
- **Effort North Star (v2026-01-29)**: Implement Search Architecture v2 to produce, persist, and rank results across multiple providers while preserving negotiation options. Approved by Lance @ 2026-01-30T04:48:59Z.
- **Definition of Done (active, v1)**:
  - **Thresholds**: search_success_rate ≥ 0.90; price_filter_accuracy ≥ 0.95; persistence_reliability = 1.0; provider_status_reporting = 1.0.
  - **Signals**: intent_extraction_accuracy (0.4); provider_adapter_activation (0.3); bid_metadata_complete (0.2); search_latency_p95 ≤ 12s (0.1).

## 1. Clarified Requirements
| Topic | Details |
| --- | --- |
| Users & Pain | Procurement teams / shoppers already exist; primary issues are inconsistent results, price filtering failures, and lost results on refresh. |
| Business Goals | Satisfy DoD metrics (above). No extra KPIs defined. |
| Scope | Full backend/BFF re-architecture per PRD. Touch frontend only when required to surface new data (e.g., provider stats, scores). |
| Constraints | Multiple providers (Rainforest, Google CSE, future ones). Maintain security (API keys server-side). Preserve negotiation by avoiding cross-provider dedupe. |

## 2. Assumptions
1. Environment has valid API keys (Rainforest, Google CSE, Gemini) and Postgres migrations can be applied.
2. Existing `/api/search` contract can be extended (provider stats, scores) without breaking clients as long as old fields persist.
3. LLM (Gemini) remains available; heuristic fallback suffices during outages.
4. Frontend changes limited to wiring new response fields + minimal UX tweaks.

## 3. Phase Plan
### Phase 1: Foundations & Migrations (Backend)
1. **Models Module** (`apps/backend/sourcing/models.py`): define `SearchIntent`, `ProviderQuery`, `RawProviderResult`, `NormalizedResult`, `RankedResult`, etc.
2. **Migrations**:
   - `rows.search_intent JSONB`
   - `rows.provider_query_map JSONB`
   - `bids.canonical_url TEXT`, `bids.source_payload JSONB`, `bids.normalized_at TIMESTAMP`, `bids.search_intent_version TEXT`
3. **Utility helpers**: canonical URL normalization, price/currency conversion service (simple FX table / stub), JSON serialization helpers.

### Phase 2: Intent Extraction Layer (BFF + Backend)
1. **BFF** (`apps/bff/src/intent/…`): new module to call LLM with structured schema (taxonomy_version, category_path). Provide fallback heuristic identical to backend.
2. **BFF `/api/search` handler**: include `search_intent` payload alongside existing query; store sanitized input.
3. **Backend** (`apps/backend/routes/rows.py` patch): accept `search_intent` on row updates; persist for auditing.
4. **Telemetry**: log extraction success/failure; metric `search_intent_extraction_success_rate`.

### Phase 3: Provider Query Adapters (Backend `sourcing/adapters`)
1. Implement base adapter + registries.
2. Implement adapters for Rainforest (Amazon), Google CSE, Mock, (placeholders for future eBay).
3. Adapters handle price filters, query keywords, category mapping (using taxonomy map defined in PRD).
4. Store per-provider query outputs in `provider_query_map` (future debugging / DoD signal).

### Phase 4: Provider Executors & Normalizers
1. Split current `SourcingProvider` classes into executors (fetch raw JSON) and normalizers (map to `NormalizedResult`).
2. Add orchestrator to run executors in parallel with timeouts, producing `ProviderExecutionResult` (with status & latency).
3. Normalizer registry ensures consistent parsing (price, merchant, image, metadata). Include `currency_original` & conversions.

### Phase 5: Aggregator + Persistence Service
1. Build `ResultAggregator` to combine normalized results, compute relevance/price/quality scores, apply post-filters (for providers lacking native filters), and keep provider-level dedupe only.
2. Implement `SourcingService` orchestrating: intent → adapters → executors → normalizers → aggregator.
3. Update `rows_search.py` to call new service, apply persistence logic using canonical URLs (upsert bids) and store `search_intent_version` + `source_payload`.
4. Update response schema to include `provider_stats`, `scores`, `user_message`, `intent echo` (for debugging) while remaining backward compatible.

### Phase 6: Frontend/BFF Wiring (Minimal)
1. **BFF** ensures `search_intent` forwarded/stored; handles provider stats and user messages from backend.
2. **Frontend**: update store/types to capture new fields (`provider_stats`, `combined_score`, etc.). Opt-in UI indicator (e.g., tooltip) but minimal layout change.
3. Add guard so UI gracefully handles partial results/unavailable providers.

### Phase 7: Observability, Validation, Rollout
1. Metrics: success rate, price accuracy, persistence, latency (Grafana/Prom). Add logging for provider query map & intent extraction confidence.
2. Automated tests:
   - Unit: adapters, normalizers, canonical URL, aggregator scoring.
   - Integration: run search with mocked providers verifying persistence + DoD thresholds.
   - E2E (Playwright): price filter scenario, refresh persistence scenario.
3. Feature flag `USE_NEW_SOURCING_ARCHITECTURE` for safe rollout; behind flag in staging, then production.
4. Documentation: update `/docs/prd/search-architecture-v2/PRD.md` references and developer setup instructions.

## 4. Detailed Task Breakdown
| Phase | Key Tasks | Owners | Deliverables |
| --- | --- | --- | --- |
| 1 | Create models module, canonical URL helper, DB migrations | Backend | `models.py`, migration scripts | 
| 2 | LLM extraction module + fallback; BFF/BK wiring | BFF/Backend | `apps/bff/src/intent/*`, updated row PATCH | 
| 3 | Adapter registry + implementations | Backend | `sourcing/adapters/*.py`, taxonomy map | 
| 4 | Executors/normalizers + orchestrator | Backend | `sourcing/executors/*.py`, `sourcing/normalizers/*.py` |
| 5 | Aggregator, persistence rules, API response updates | Backend | `sourcing/service.py`, updated `rows_search.py` |
| 6 | Minimal FE wiring for provider stats/scores | Frontend | store/types/components adjustments |
| 7 | Metrics, tests, rollout flag + docs | Full stack | dashboards, tests, feature flag, docs |

## 5. Testing & Validation Strategy
1. **Unit Tests**: adapters (input → provider query), normalizers (raw result → normalized object), canonical URL logic, aggregator scoring (bounded price/quality).
2. **Integration Tests** (pytest): simulate multi-provider response, verify persistence, provider stats added, price filters enforced.
3. **Contract Tests** (BFF ↔ backend): ensure `search_intent`, `provider_query_map`, `provider_stats` flows.
4. **E2E Tests** (Playwright):
   - Price range search persists after refresh
   - Provider failure scenario shows partial results + message
5. **Manual Validation**: run real searches (bikes <$5k, etc.) verifying DoD metrics on dashboards.

## 6. Observability
- Add counters/histograms for DoD metrics: `search_success_rate`, `price_filter_accuracy`, `persistence_reliability`, `provider_status_reporting`, plus `provider_execution_latency_ms` per provider.
- Log structured entries with `search_intent_id`, `provider_query_map`, `bid canonical_url`, sanitized input.

## 7. Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Provider API schema drift | Normalizers break | Defensive parsing, validation tests, fallback provider statuses |
| LLM failure/unavailable | Intent extraction incomplete | Heuristic fallback, log + metric alerts |
| Latency inflation | Users wait >12s | Parallel execution, per-provider timeout, partial results streaming |
| DB migration / canonical URL bugs | Duplicate bids / data loss | Back up before migration, add unique index on `(row_id, canonical_url, source)` |
| Frontend mismatch | UI not showing new data | Feature flag + minimal UI wires early |

## 8. Next Steps
1. Implement Phase 1 foundations & migrations.
2. Proceed sequentially through phases, keeping FE touches minimal.
3. Maintain `PROGRESS.md` as phases complete; update DoD evidence as metrics collected.
