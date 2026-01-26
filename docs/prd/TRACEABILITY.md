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
