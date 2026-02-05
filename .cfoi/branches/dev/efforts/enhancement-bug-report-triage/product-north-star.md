# Effort North Star (Effort: bug-report-triage, v2026-02-05)

## Goal Statement
Add intelligent triage to classify incoming user reports as bugs vs feature requests, routing each appropriately.

## Ties to Product North Star
- **Product Mission**: "Transparent provider status (partial results over silence)" — this extends transparency to the bug/feedback pipeline
- **Supports Metric**: Operational efficiency — reduces noise in bug queue, ensures feature requests don't get lost

## In Scope
- AI-powered classification of incoming reports (bug vs feature request)
- Bug reports: continue existing AI Bug Fixer flow (GitHub issue → Claude fix)
- Feature requests: notify you (Lance) for later review — exact notification method TBD (email, Slack, dashboard, etc.)
- Classification confidence threshold — low confidence reports flagged for manual review

## Out of Scope
- Automated feature request implementation
- User-facing feature request tracking/voting
- Changes to the existing bug fix flow (only adding triage before it)

## Acceptance Checkpoints
- [ ] Reports are classified with >85% accuracy (bug vs feature)
- [ ] Bugs continue through existing AI Bug Fixer pipeline unchanged
- [ ] Feature requests trigger notification to Lance
- [ ] Low-confidence classifications are flagged for manual review

## Dependencies & Risks
- **Dependencies**: Existing bug reporter modal, bugs.py backend route
- **Risks**: Classification accuracy — may need tuning; notification delivery reliability

## Approver / Date
- Approved by: [Pending]
- Date: [Pending]
