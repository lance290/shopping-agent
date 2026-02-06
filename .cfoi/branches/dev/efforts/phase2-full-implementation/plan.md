# Plan: Phase 2 Full Implementation

## Problem Statement
8 Phase 2 PRDs remain. Codebase audit reveals most backend routes, models, and email services already exist. The gaps are primarily frontend integration, missing UI features, and two entirely new features (Merchant Registry, DocuSign).

## Codebase State Summary (verified)

| PRD | Backend Status | Frontend Status | Real Gap |
|-----|---------------|-----------------|----------|
| Likes & Comments | ✅ routes/likes.py, routes/comments.py, Like/Comment models | ✅ RowStrip loads likes/comments, optimistic UI | Show like/comment counts on tiles, aria-pressed |
| Share Links | ✅ routes/shares.py, ShareLink model, metrics | ⚠️ API helpers in api.ts, no share page | Add /share/[token] page, wire tile share button to backend API |
| Quote Intake | ✅ routes/quotes.py, SellerQuote model | ✅ /quote/[token] page exists | Generalize form beyond private jets to use dynamic choice factors |
| WattData Outreach | ✅ routes/outreach.py, OutreachEvent model | ✅ Service detection flow | Add 48h reminder cron, implement unsubscribe endpoint |
| Email Handoff | ✅ DealHandoff model, select_quote with emails | ✅ SelectQuoteModal | Add "Mark as Closed" endpoint + UI, deal status tracking |
| Stripe Checkout | ⚠️ clickout.py (affiliate only) | ❌ No Buy Now flow | Add PurchaseEvent model, Stripe checkout session, purchase tracking |
| Merchant Registry | ❌ Nothing | ❌ Nothing | New: Merchant model, registration API, matching, dashboard |
| DocuSign Contracts | ❌ Nothing | ❌ Nothing | New: Contract model, DocuSign API integration |

## Approach: Gap-Fill by PRD

### 1. Likes & Comments (gap-fill, ~30 min)
**What exists**: Full backend CRUD (likes.py:290 lines, comments.py:120 lines), Like/Comment models, toggle endpoint, RowStrip loads likes/comments on mount with mergeLikes/mergeComments, optimistic UI.
**Gaps to fill**:
- OfferTile: show like_count and comment_count badges on heart/comment buttons
- OfferTile: add `aria-pressed={isLiked}` to like button
- Backend: GET /bids/{bid_id}/social already returns like_count, is_liked, comment_count — frontend just needs to display them
- Add bulk likes/comments loading to avoid N+1 on row load (GET /likes?row_id= already exists)

**Decision**: Counts are already available via fetchLikesApi per-row. Show count badges on OfferTile buttons when count > 0. No new backend work needed.

### 2. Share Links (gap-fill, ~45 min)
**What exists**: Backend shares.py (364 lines) with create/resolve/metrics, ShareLink model with access_count, API helpers createShareLink/resolveShareLink in api.ts.
**Gaps to fill**:
- Create `/share/[token]` Next.js page that resolves the share link and renders content read-only
- Wire OfferTile's share button to call createShareLink() then copy the URL (currently copies raw offer URL)
- Wire RowStrip's handleCopySearchLink to use createShareLink for rows

**Decision**: The share page should resolve the token, fetch content via the public API, and render a read-only view. For tiles: create share link via API then copy. For rows: create share link via API then copy.

### 3. Quote Intake (gap-fill, ~30 min)
**What exists**: routes/quotes.py (335 lines), /quote/[token] page (269 lines).
**Gaps to fill**:
- Quote form is hardcoded with `aircraftType` and `includesCatering` fields
- Should dynamically render choice_factors from the backend QuoteFormData response
- Backend already sends choice_factors array from row — frontend ignores it

**Decision**: Replace hardcoded fields with dynamic rendering of `formData.choice_factors`. Each factor has `name`, `label`, `type` (text/boolean/select). Render appropriate input for each type.

### 4. WattData Outreach (gap-fill, ~30 min)
**What exists**: routes/outreach.py (383 lines), email service, tracking.
**Gaps to fill**:
- No 48h reminder email to non-responders (PRD requirement)
- Unsubscribe link is placeholder `#` in email template
- Need unsubscribe endpoint: GET /outreach/unsubscribe/{token}

**Decision**: Add send_reminder_email function to email.py. Add unsubscribe endpoint to outreach.py that sets opt_out=True on OutreachEvent. Add reminder logic as a utility function (cron is out of scope for MVP, but the function should exist and be callable).

### 5. Email Handoff (gap-fill, ~30 min)
**What exists**: DealHandoff model with status field, select_quote in quotes.py sends emails.
**Gaps to fill**:
- No "Mark as Closed" endpoint (POST /quotes/{quote_id}/close or PATCH /handoffs/{id})
- No UI for buyer to mark deal as closed
- No deal tracking status display

**Decision**: Add PATCH /handoffs/{handoff_id}/close endpoint. Add "Mark as Closed" button to the row when status is "closed" (meaning selected). Show deal status badge on selected tiles.

### 6. Stripe Checkout (new integration, ~60 min)
**What exists**: clickout.py with affiliate tracking, ClickoutEvent model.
**Gaps to fill**:
- No PurchaseEvent model for tracking completed purchases
- No Stripe Checkout Session creation
- No "Buy Now" button distinction on retail tiles
- For MVP: affiliate clickout is the primary flow, Stripe is for future direct purchases

**Decision**: Add PurchaseEvent model. For MVP, focus on affiliate tracking enhancement: track when user clicks "Buy Now" on retail tiles with proper attribution. Stripe Checkout Session creation requires API keys and merchant onboarding — create the endpoint scaffold but don't require live Stripe for MVP. Add "Buy Now" label to retail tiles.

### 7. Merchant Registry (new feature, ~90 min)
**What exists**: Nothing.
**Gaps to fill**:
- Merchant model (name, email, phone, website, categories, service_areas, status)
- Registration API endpoint (POST /merchants/register)
- Merchant dashboard (GET /merchants/me, GET /merchants/me/rfps)
- Priority matching algorithm
- Frontend registration page (/merchants/register)
- Source badges on tiles ("Verified Partner")

**Decision**: Create Merchant model, registration endpoint, basic dashboard API. Priority matching adds registered merchants to search results before WattData. Frontend: registration page and badge rendering.

### 8. DocuSign Contracts (new feature, ~60 min)
**What exists**: Nothing.
**Gaps to fill**:
- Contract model (bid_id, buyer_id, seller_email, status, docusign_envelope_id)
- Contract creation endpoint
- DocuSign API integration (envelope creation, webhook for status)
- Contract status tracking

**Decision**: Create Contract model and endpoints. DocuSign API integration requires API keys — create the scaffold with a mock/demo mode similar to email service pattern. Contract generation from templates, envelope sending, webhook handler for signature tracking.

## Gap Review #1 Findings

After first review, identified these additional gaps:

1. **Likes & Comments**: RowStrip's comment handler uses `window.prompt()` — should be a proper modal for better UX. But this is cosmetic, not a persistence gap. Keep as-is for MVP.

2. **Share Links**: The resolve endpoint increments access_count but doesn't track unique_visitors. Need to add session/cookie-based unique tracking. For MVP, access_count is sufficient.

3. **Quote Intake**: The `QuoteSubmission` model has hardcoded `aircraft_type` and `includes_catering` fields. These should remain as optional fields for backward compatibility, but the `answers` dict should be the primary vehicle for choice factor answers.

4. **Merchant Registry**: Need to define the category taxonomy in a seed file or config, not hardcode in the model. The PRD provides the taxonomy.

5. **Stripe Checkout**: The PRD mentions "Buy Now" button on eligible retail tiles. Need to define what makes a tile "eligible" — any non-service-provider tile with a valid URL is eligible for affiliate clickout.

6. **Cross-cutting**: All new endpoints need auth via get_current_session. All new models need proper indexes.

## Gap Review #2 Findings

After second review, checking for DRY violations and missing test coverage:

1. **DRY**: email.py has repeated Resend send logic — should extract a shared `_send_email(to, subject, html, text)` helper. Will do this when adding reminder email.

2. **DRY**: RowStrip's getCanonicalOfferUrl duplicates store.ts's extractInnerUrl logic. Not fixing in this effort (pre-existing).

3. **Tests**: Need backend tests for new endpoints (unsubscribe, close handoff, merchant registration). Frontend tests for share page, dynamic quote form.

4. **Missing**: No frontend proxy route for `/api/shares` — need to check if proxy catches it. The proxy in `apps/frontend/app/api/proxy/[...path]/route.ts` should handle it since shares.py uses `/api/shares` prefix.

5. **Missing**: The quotes.py `select_quote` endpoint lacks auth — it should require authentication. This is a pre-existing security gap but important to note.

## Implementation Order (by dependency)
1. Likes & Comments (foundation for shares)
2. Share Links (depends on tiles having like counts)
3. Quote Intake generalization
4. WattData Outreach (reminder + unsubscribe)
5. Email Handoff (close endpoint)
6. Stripe Checkout (purchase tracking)
7. Merchant Registry (new infrastructure)
8. DocuSign Contracts (new infrastructure)
