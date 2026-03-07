# PRD: EA Bulk Outreach

**Audience:** Engineering / product review  
**Status:** Draft  
**Product:** Buy Anything  
**Depends on:** PRD 01 (EA Network), PRD 02 (Quote-to-Payment)  
**Primary goal:** Let an EA contact multiple vendors for the same request in one action, with a preview step before anything sends.

---

## 1. Summary

When an EA searches for a high-consideration item (private jet charter, bespoke menswear, executive relocation), the search pipeline returns vendor directory matches alongside product results. Today those vendor results appear as offer cards, but the EA has no in-product way to blast a quote request to multiple vendors at once.

The backend infrastructure for bulk outreach is **already fully built** across three complementary systems. The frontend component (`OutreachQueue`) is also built but not wired into the rendered UI. This PRD documents the existing infrastructure, defines the intended UX, and specifies the remaining wiring work.

---

## 2. Current State (Audit)

### Backend — fully implemented

| System | Route file | Purpose | Status |
|--------|-----------|---------|--------|
| **Campaign drafts** | `routes/outreach_campaigns.py` | LLM drafts personalized email per vendor. EA reviews/edits each draft, then approves individually or bulk. | Working |
| **Template blast** | `routes/outreach_blast.py` | Single template with `{{vendor_name}}`, `{{vendor_company}}`, `{{row_title}}` placeholders. Dry-run preview. Deduplicates against already-contacted vendors. | Working |
| **Category trigger** | `routes/outreach.py` | Triggers outreach by vendor category from the VendorProfile directory with magic-link quote forms. | Working |
| **Tracking** | `routes/outreach_tracking.py` | Open/click/quote-submitted tracking per vendor, with tracking pixels and status endpoints. | Working |
| **Outreach service** | `services/outreach_service.py` | Campaign orchestration: draft, approve, send, pause. LLM email generation per vendor type. | Working |

Key backend features already in place:
- **Deduplication**: blast skips vendors already contacted for the same row
- **Dry-run mode**: `POST /outreach/rows/{row_id}/blast` with `dry_run: true` returns previews without sending
- **Tracking pixels**: open detection via 1x1 pixel
- **Magic-link quotes**: vendors receive a unique link to submit their quote without logging in
- **Unsubscribe links**: CAN-SPAM compliant
- **Admin alerts**: platform notified on blast sends
- **Action budgets**: campaigns have a configurable action budget to cap outreach volume

### Frontend — built but not wired

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| **OutreachQueue** | `components/OutreachQueue.tsx` (460 LOC) | Full modal flow: select vendors → capture sender info → AI drafts personalized emails → preview with tabs → "Approve & Send All" → success toast | Built, **not rendered** |
| **API layer** | `utils/api-outreach.ts` (194 LOC) | `createOutreachCampaign`, `approveAndSendCampaign`, `fetchContactStatuses`, `createQuoteLink`, `sendOutreachEmail`, `generateOutreachEmail` | Working |
| **Proxy routes** | `app/api/outreach/campaigns/*` | Full CRUD proxy routes for campaign creation, approval, pause, per-message approval, row lookup | Working |

### What's missing

| Gap | Effort |
|-----|--------|
| `OutreachQueue` is never imported or rendered by `VerticalListRow` or any other active component | ~5 lines |
| No SDUI intent for triggering bulk outreach from a deal/action row | Small — add `bulk_outreach` intent or render `OutreachQueue` conditionally |
| Blast endpoint (`outreach_blast.py`) has no frontend UI — only the campaign-draft flow has a UI | Medium — could be exposed as a simpler "quick blast" option alongside the AI-drafted flow |
| `VendorContactModal` (single-vendor outreach) and `OutreachQueue` (multi-vendor) aren't coordinated — EA could accidentally contact the same vendor through both paths | Small — dedup check on send |

---

## 3. Problem Statement

The EA finds 5-15 vendor matches for a high-consideration request. Today, the EA must:
1. Click into each vendor card individually
2. Use the `VendorContactModal` to send one email at a time
3. Repeat for every vendor

This is too slow for the primary EA workflow. The EA should be able to:
1. See all vendor matches
2. Select which ones to contact (or select all)
3. Preview what will be sent
4. Send in one action

The infrastructure exists. It just needs to be surfaced.

---

## 4. Goals

### Goals
- Wire `OutreachQueue` into the row view so EAs see it when vendor results are present
- Preserve the preview-before-send guardrail (EA always sees what's going out)
- Include the viral BuyAnything footer and "Try BuyAnything" CTA in every outreach email
- Track opens, clicks, and quote submissions per vendor per row
- Deduplicate: never double-contact a vendor for the same row

### Non-goals
- Fully automated outreach without EA review (rejected in product discussion)
- Rebuilding the outreach backend (it's done)
- Building a separate blast UI for the template-based flow (campaign-draft flow is sufficient for v1)
- Outreach from unauthenticated/public search (EA must be logged in)

---

## 5. User Experience

### 5.1 Happy path: EA bulk-contacts vendors
1. EA searches for "private jet charter SAN to ASE."
2. Search returns 8 vendor directory matches + product results.
3. Below the offer cards, the EA sees the **OutreachQueue** panel:
   - Header: "Service Providers (8)" with a sparkle icon
   - Vendor cards in a grid, each with:
     - Vendor name and match reasons (e.g., "Strong match to your request")
     - Email address preview
     - Selectable checkbox
     - Individual "Select" button
4. EA selects 5 vendors (or clicks "Send to 5 Vendors" header button).
5. Modal opens:
   - If sender name/email not cached → brief capture form
   - AI drafts personalized emails for each selected vendor
   - Drafting spinner: "AI is classifying vendors and drafting personalized emails..."
6. Review screen:
   - Tab per vendor showing the drafted email
   - Each email shows: To, Subject, Reply-to, body text, deal card preview
   - Warning banner: "Review each email above. Every email includes a deal card, a tracked quote link, and our Try BuyAnything viral footer."
7. EA clicks **"Approve & Send All (5)"**.
8. Sending spinner → success toast: "Emails sent successfully!"
9. Sent vendors show green "Sent" badges in the OutreachQueue.

### 5.2 Single-vendor path (unchanged)
- EA can still use `VendorContactModal` for individual vendor outreach from the offer card.
- The `OutreachQueue` deduplicates: if a vendor was already contacted via `VendorContactModal`, they show as "Sent" in the queue.

### 5.3 Viral loop in every email
Every outreach email includes:
- BuyAnything branding in the footer
- "Sent on behalf of [EA Name] via BuyAnything" attribution
- Platform disclosure: "BuyAnything.ai is a marketplace platform..."
- The **deal card** with the request summary
- A tracked quote submission link

This is the primary viral acquisition channel: vendors who receive outreach become aware of BuyAnything and may sign up as buyers.

---

## 6. Backend Requirements

### Already implemented — no changes needed
- `POST /outreach/campaigns` — create campaign with LLM-drafted emails
- `POST /outreach/campaigns/{id}/approve-all` — approve and send all drafts
- `POST /outreach/campaigns/{id}/send` — send approved messages
- `POST /outreach/campaigns/{id}/pause` — emergency stop
- `POST /outreach/campaigns/messages/{id}/approve` — approve single message with optional edits
- `GET /outreach/campaigns/{id}` — get campaign with messages and quotes
- `GET /outreach/campaigns/row/{row_id}` — get all campaigns for a row
- `POST /outreach/rows/{row_id}/blast` — template blast with dry-run
- `GET /outreach/rows/{row_id}/status` — tracking status (sent/opened/clicked/quoted)

### Optional future enhancement
- `POST /outreach/rows/{row_id}/blast` could be exposed as a "quick blast" option in the UI for EAs who want to skip the AI-drafting step and use a simpler template.

---

## 7. Frontend Requirements

### 7.1 Wire OutreachQueue into VerticalListRow
When a row has vendor directory results (`source === 'vendor_directory'`), render the `OutreachQueue` component below the offer cards.

Props needed:
- `rowId` — the current row ID
- `desireTier` — from `row.desire_tier` (controls the header label: "Service Providers" vs "Specialists" vs "Matched Vendors")
- `offers` — the full offers array (OutreachQueue filters to `vendor_directory` internally)

### 7.2 Conditional rendering
- Only render if there are `vendor_directory` offers in the results
- Only render for authenticated users
- Don't render if the row has no bids yet (still searching)

### 7.3 Already-contacted dedup
The `OutreachQueue` already handles this: sent vendors show green "Sent" badges. But we should also check the `outreach_status` from `fetchContactStatuses` to mark vendors contacted through `VendorContactModal`.

---

## 8. Acceptance Criteria

### Frontend
- EA viewing a row with vendor results sees the OutreachQueue panel
- EA can select vendors and trigger the AI-drafted campaign flow
- EA sees email previews before sending
- EA can approve and send all in one click
- Sent vendors show "Sent" badges
- OutreachQueue does not appear for rows without vendor results

### Backend (already passing — regression only)
- Campaign creation drafts personalized emails per vendor
- Approve-all sends all messages
- Tracking pixels work (opens detected)
- Magic-link quotes are generated per vendor
- Deduplication prevents double-contacting

### Viral loop
- Every sent email includes BuyAnything branding
- Every sent email includes the deal card
- Every sent email includes platform disclosure

---

## 9. Testing Plan

### Frontend
- Render a row with vendor_directory offers → OutreachQueue appears
- Render a row without vendor results → OutreachQueue does not appear
- Select vendors → modal opens → AI drafts emails → preview renders
- Approve & send → success toast → sent badges appear

### Backend (existing tests)
- Campaign creation with LLM drafting
- Approve-all and send flow
- Blast with dry-run preview
- Tracking status endpoint
- Deduplication on blast

### Regression
- Single-vendor outreach via VendorContactModal still works
- Rows without deals/vendors render as before
- Search results display unaffected

---

## 10. Implementation Order

1. Import `OutreachQueue` in `VerticalListRow.tsx`
2. Add conditional render when vendor results are present
3. Verify the existing modal flow works end-to-end
4. Test deduplication across OutreachQueue and VendorContactModal paths
5. Push

---

## 11. Open Questions

1. Should the blast template endpoint also get a frontend UI, or is the AI-drafted campaign flow sufficient for v1?
2. Should there be a daily send limit per EA to prevent abuse?
3. Should the EA be able to customize the deal card content before sending?
4. Should we track which outreach emails lead to vendor sign-ups (attribution for the viral loop)?
