# PRD Traceability

## Parent → Child PRDs

| Parent PRD folder (slug) | Child PRD name | Priority | Phase | Ship Order | Status | Dependencies |
|---|---|---|---|---:|---|---|
| ai-bug-fixer | prd-report-bug-ux.md | P0 | MVP | 1 | Draft | - |
| ai-bug-fixer | prd-bug-report-storage-status.md | P0 | MVP | 2 | Draft | prd-report-bug-ux.md |
| ai-bug-fixer | prd-github-issue-claude-trigger.md | P0 | MVP | 3 | Draft | prd-bug-report-storage-status.md |
| ai-bug-fixer | prd-diagnostics-redaction.md | P1 | v1.1 | 4 | Draft | prd-bug-report-storage-status.md |
| ai-bug-fixer | prd-verification-loop-preview-url.md | P1 | v1.1 | 5 | Draft | prd-github-issue-claude-trigger.md |
| ai-bug-fixer | prd-polish-routing-notifications.md | P2 | Future | 6 | Draft | prd-report-bug-ux.md |
| marketplace-pivot | prd-workspace-tile-provenance.md | P0 | MVP | 1 | Draft | - |
| marketplace-pivot | prd-multi-channel-sourcing-outreach.md | P0 | MVP | 2 | Draft | prd-workspace-tile-provenance.md |
| marketplace-pivot | prd-seller-tiles-quote-intake.md | P0 | MVP | 3 | Draft | prd-workspace-tile-provenance.md |
| marketplace-pivot | prd-unified-closing-layer.md | P1 | v1.1 | 4 | Draft | prd-seller-tiles-quote-intake.md |
| phase2 | prd-tile-provenance.md | P0 | MVP | 1 | Draft | - |
| phase2 | prd-likes-comments.md | P0 | MVP | 2 | Draft | - |
| phase2 | prd-share-links.md | P0 | MVP | 3 | Draft | - |
| phase2 | prd-quote-intake.md | P1 | v1.1 | 4 | Draft | prd-wattdata-outreach.md |
| phase2 | prd-wattdata-outreach.md | P1 | v1.1 | 5 | Draft | - |
| phase2 | prd-stripe-checkout.md | P2 | v2.0 | 6 | Draft | - |
| phase2 | prd-docusign-contracts.md | P2 | v2.0 | 7 | Draft | prd-quote-intake.md |
| phase3 | 01-stripe-checkout.md | P0 | v3.0 | 1 | Implemented | - |
| phase3 | 02-wattdata-mcp.md | P0 | v3.0 | 2 | Scaffold | - |
| phase3 | 03-seller-dashboard.md | P1 | v3.0 | 3 | Implemented | 01-stripe-checkout.md |
| phase3 | 04-provenance-enrichment.md | P1 | v3.0 | 4 | Implemented | - |
| phase3 | 05-social-polish.md | P1 | v3.0 | 5 | Implemented | - |
| phase3 | 06-admin-dashboard.md | P2 | v3.0 | 6 | Implemented | - |
| phase3 | 07-mobile-responsive.md | P2 | v3.0 | 7 | Implemented | - |
