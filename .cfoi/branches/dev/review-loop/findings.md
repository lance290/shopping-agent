# Review Findings - feature-discovery-quality-gating

## Findings
- Fixed before push: the discovered-result persistence guardrail in [service.py](/Volumes/PivotNorth/Shopping%20Agent/apps/backend/sourcing/service.py) had copied the row-visibility threshold as a literal `0.55` instead of reusing the config-driven threshold helper. That would have caused drift between row visibility and persistence behavior.
- Fixed before push: the candidate-type heuristic order in [classification.py](/Volumes/PivotNorth/Shopping%20Agent/apps/backend/sourcing/discovery/classification.py) could classify mixed-signal listing pages as marketplaces before the listing-page check ran. That was too permissive for brokerage searches.
- No further critical findings remained after the targeted review pass and test rerun.

## Residual Risks
- Shallow-fetch classification enrichment is config-gated and off by default, so some ambiguous candidates will still rely on snippet/domain evidence alone until that is enabled in a live environment.
- The current rerank path depends on external LLM availability for the richer ranking pass; fallback is safe, but production quality will still vary with key availability and provider behavior.
- Real-world QA is still needed against live real-estate, whisky, yacht charter, and aircraft queries with external search APIs configured.
