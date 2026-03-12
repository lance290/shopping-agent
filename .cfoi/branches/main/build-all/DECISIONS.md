# Build-All Decisions Log

## PRD: Trusted Search & Vendor Network Refactor

### Decision 1: Scope to Phase 1 + Phase 2 only for this build
**Rationale:** Phase 3 (EA Curation) and Phase 4 (Miss Discovery) require frontend UI work and new API endpoints that are best built after the trust model is validated. Phase 1 + 2 are backend-focused and independently testable.

### Decision 2: QueryProfile is prompt-only, not a separate model/table
**Rationale:** The existing agent loop already makes tool-selection decisions. Adding structured reasoning to the prompt is cheaper and faster than adding a new LLM call or DB model. We log the profile signals in the SSE stream for debugging.

### Decision 3: Extend Vendor model in-place, no child tables
**Rationale:** Vendor already has 30+ fields. Adding ~8 more columns is simpler than creating VendorContact/VendorTrust child tables. The existing AuditLog handles edit tracking.

### Decision 4: VendorEndorsement table ships in Phase 2, not Phase 3
**Rationale:** The endorsement model is needed for trust scoring (Phase 2). EA UI to create endorsements is Phase 3, but the table/API must exist first.

### Decision 5: Migration naming follows existing pattern
**Rationale:** Existing migrations use `s{NN}_description` format. Next is s19.

### Decision 6: Fix search_web tool description in Phase 1
**Rationale:** The current description says "editorial content, 'best of' lists" which contradicts commercial intent. This is a known bug from the prior audit session.

### Decision 7: contact_quality_score is computed, not stored
**Rationale:** Computing it from field presence (phone, email, website, contact_name) avoids stale scores and migration overhead. trust_score IS stored because it blends multiple signals including endorsements.
