# Build-All Decisions Log

## 2026-02-15: Build Order
**Decision**: Implement in dependency order: Desire Classification → Quantum Re-Ranking → Autonomous Outreach
**Reason**: PRD 1 is prerequisite. PRD 3 has no new UI. PRD 2 is largest scope.

## 2026-02-15: Desire Classification — Implementation Approach
**Decision**: Extend existing `UnifiedDecision` model with `desire_tier` + `desire_confidence` fields rather than creating a separate classification service.
**Reason**: The LLM already runs once per chat turn in `make_unified_decision()`. Adding tier classification to the same prompt avoids an extra LLM call. Classification is lightweight enough to fit in the existing prompt.

## 2026-02-15: Backward Compatibility
**Decision**: Not a concern per user instruction. Breaking changes are acceptable.
**Reason**: User explicitly stated "backwards code compatibility is not a concern."

## 2026-02-15: _fetch_vendors() Dead Code
**Decision**: Remove entirely from chat.py. 
**Reason**: Calls deleted endpoints (`/outreach/vendors/{category}`, `/outreach/rows/{row_id}/vendors`). Adds 15s timeout latency. Vendor results now flow through `vendor_directory` provider in the search pipeline.

## 2026-02-15: Quantum Re-Ranking — Simulation Mode Only
**Decision**: Use Strawberry Fields simulation mode, not Xanadu hardware.
**Reason**: No quantum cloud API key needed. Results are mathematically identical. Latency acceptable for reranking ≤50 results.

## 2026-02-15: Autonomous Outreach — Email Provider
**Decision**: Use Resend (already in requirements.txt) for outbound email delivery.
**Reason**: Already a dependency. Simpler API than SendGrid. Good deliverability.

## 2026-02-15: Autonomous Outreach — Inbound Email
**Decision**: Defer inbound email processing to Level 2. Level 1 MVP is draft & send only.
**Reason**: Inbound email requires a mail domain, DNS config, and webhook infrastructure. Draft & send alone is transformative for the EA workflow.
