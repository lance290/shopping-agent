# Plan — feature-discovery-quality-gating

## Goal
Clean the BuyAnything live discovery candidate pool before ranking by adding:

- evidence-driven candidate classification
- discovery-mode admissibility gating
- safer provenance defaults
- LLM-assisted reranking with heuristic fallback
- audit-friendly debug records

## Execution Strategy
1. Tighten discovery candidate provenance at the adapter seam.
2. Classify and gate candidates inside `DiscoveryOrchestrator`.
3. Normalize only admitted candidates into row-visible results.
4. Add LLM rerank as a post-gating enhancer, not a truth engine.
5. Cover the real failure modes with focused regression tests.

## Scope
- Backend only
- BuyAnything vendor discovery path only
- No commodity-path changes
