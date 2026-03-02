# PRD: JetBid Demo — Tim Connors Charter Quote Request

**Priority:** P0 — Demo-blocking  
**Target:** Send RFQ to 10+ charter vendors by Feb 8–9, 2026  
**Stakeholder:** Tim Connors (tconnors@gmail.com)  
**URL:** https://frontend-dev-aca4.up.railway.app  

---

## 1. Context

Tim Connors needs to send quote requests to 10–12 private jet charter vendors for a round-trip light jet charter (BNA ↔ FWA, Feb 13–15). He has a specific vendor list, specific itinerary details, and wants quotes returned to his email.

This PRD covers the **minimum changes** required to make the demo work end-to-end without embarrassing bugs. No speculative features — only fixes and polish for what Tim will actually touch.

---

## 2. Tim's Itinerary (Source of Truth)

### Leg 1 — Outbound
| Field | Value |
|-------|-------|
| Route | BNA → FWA |
| Date | Friday, Feb 13, 2026 |
| Wheels up | 2:00 PM Central |
| Arrival | ~4:00 PM Eastern |
| Passengers | Wendy Connors, Margaret Oppelt |
| Aircraft | Light jet with Wi-Fi (Starlink ideal) |

### Leg 2 — Return
| Field | Value |
|-------|-------|
| Route | FWA → BNA |
| Date | Sunday, Feb 15, 2026 |
| Wheels up | 2:30 PM Eastern |
| Arrival | ~2:30 PM Central |
| Passengers | Timothy Connors, Wendy Connors, Margaret Oppelt |
| Aircraft | Same |

### Requirements
- Round-trip quote (not two one-ways)
- Wi-Fi required (Starlink preferred)
- Light jet category
- Quotes returned to **tconnors@gmail.com**

---

## 3. Codebase Audit Findings

### 3.1 Vendor Data — `apps/backend/services/vendors.py`

**Status: 11/12 vendors present, 1 missing, 1 misclassified**

| # | Vendor | Email | In System? | Issue |
|---|--------|-------|-----------|-------|
| 1 | JetRight | charter@jetrightnashville.com | ✅ | Tim's primary — send last |
| 2 | 24/7 Jet | adnan@247jet.com | ✅ | — |
| 3 | WCAS | charter@wcas.aero | ✅ | — |
| 4 | **Brett Driscoll** | brett.driscoll2@gmail.com | ❌ **MISSING** | Must add |
| 5 | Business Jet Advisors | info@businessjetadvisors.com | ✅ | Flagged as "not a charter provider" — remove caveat, Tim wants quotes from all |
| 6 | flyExclusive | mmorrissey@flyexclusive.com | ✅ | — |
| 7 | Airble | info@airble.com | ✅ | — |
| 8 | V2 Jets | jkessler@v2jets.com | ✅ | — |
| 9 | FXAIR | michael.hall@fxair.com | ✅ | — |
| 10 | Jet Access | cparker@flyja.com | ✅ | — |
| 11 | Peak Aviation | charter@peakaviationsolutions.com | ✅ | — |
| 12 | V2 Jets (alt) | fly@v2jets.com | ✅ | Duplicate contact — keep for now |

### 3.2 Options Card Auto-Fill — `RequestTile.tsx` + `ChoiceFactorPanel.tsx`

**Current flow:**
1. User chats → BFF LLM extracts `intent.constraints` (e.g., `{ origin: "BNA", destination: "FWA", date: "Feb 13", passengers: 2 }`)
2. Row created with `choice_answers = JSON.stringify(constraints)`
3. BFF calls `generateAndSaveChoiceFactors()` — LLM generates factor definitions (name/label/type/options)
4. BFF sends `factors_updated` SSE event with full row data
5. Chat.tsx handles event, updates store → RequestTile renders factors
6. RequestTile merges `choice_answers` into local state → fields pre-fill

**Bug B1 — Constraint key mismatch (CRITICAL):**
The LLM might extract constraints with keys like `origin`, `destination` but generate choice factors with names `from_airport`, `to_airport`. The `choice_answers` values are keyed by the constraint names, but the UI renders factors by their `name` field. If they don't match, **values won't pre-fill**.

The `generateAndSaveChoiceFactors` prompt includes: *"IMPORTANT: If 'Existing constraints' are provided, you MUST include a spec definition for each constraint key so the UI can display it."* — but LLM compliance is not guaranteed.

**Fix:** After generating factors, programmatically verify every key in `choice_answers` has a matching factor `name`. If not, rename the factor `name` to match, or copy the answer to the factor's name. This is a backend/BFF concern.

**Bug B2 — Generic fallback factors:**
`RequestTile` detects generic fallback factors (`max_budget`, `preferred_brand`, `condition`, `shipping_speed`, `notes`) and auto-regenerates. This is correct for products but could fire for services if the LLM generates similarly-named factors. Low risk for aviation since the prompt includes specific aviation factor examples.

**Bug B3 — Polling race (LOW RISK):**
`RequestTile` polls every 2s up to 4 times for missing factors. In the unified chat path, factors are generated synchronously and sent via SSE before `done`. The poll is a safety net. Low risk.

### 3.3 VendorContactModal — Sizing & Content

**Bug B4 — Modal too narrow (CRITICAL):**
`max-w-md` = 448px. For a round-trip itinerary with passenger manifests, time zones, and special requirements, this is unusable. The email body textarea has `rows={6}` — shows ~6 lines of a message that's typically 15–25 lines.

**Fix:** Widen to `max-w-2xl` (672px). Increase textarea to `rows={14}` minimum. Add vertical scroll if needed.

**Bug B5 — "Wheels up" time not extracted (CRITICAL):**
The `defaultOutreach` useMemo extracts time from `fields.time_fixed`, `fields.time_earliest`, `fields.time_latest` — but does NOT fall back to common constraint keys like `wheels_up`, `wheels_up_time`, `departure_time`, `time`.

```typescript
// CURRENT (broken for "wheels_up_time"):
const time = timeMode === 'fixed' ? (timeFixed || '') : ...;

// MISSING: extract() fallback for time keys
```

**Fix:** Add time extraction: `extract('wheels_up', 'wheels_up_time', 'departure_time', 'time', 'wheels_up_time_leg1')`.

**Bug B6 — No round-trip support (CRITICAL):**
The modal has single-leg fields (one from, one to, one date, one time). Tim's request is round-trip with different passenger counts per leg and different time zones.

**Fix:** When `trip_type === 'round-trip'`, show a second set of fields (return date, return time, return passengers). The email body template must include both legs.

**Bug B7 — Passenger names not captured:**
Tim needs to include specific passenger names (Wendy Connors, Margaret Oppelt on outbound; + Timothy Connors on return). The modal has a generic "Passengers" count field but no names field.

**Fix:** Add a "Passenger names" text area below the count field.

**Bug B8 — Reply-to email not configurable:**
Tim wants quotes returned to `tconnors@gmail.com`. The modal opens the user's local email client via `mailto:` — so replies go to whatever email the user's client uses. But the email body template should explicitly include a reply-to line: "Please reply to: tconnors@gmail.com".

**Fix:** Add a "Reply-to email" field in the modal. Include it in the email body.

### 3.4 Email Body Template

**Current template** (in `vendors.py: CHARTER_EMAIL_TEMPLATE`):
- Single-leg only
- Generic placeholders `[Route]`, `[Dates]`, `[Passengers]`
- Asks for detailed info (safety certs, cancellation policy, etc.)
- Good structure but needs round-trip support

**Fix:** The VendorContactModal's `bodyTemplateRaw` default should handle round-trip. The template from `vendors.py` is a reference but not directly used by the modal — the modal has its own inline default template.

### 3.5 Bid Persistence on Reload

**Status: Working correctly.**
- Vendors are persisted as `Bid` records with `is_service_provider=True`
- `Bid` has `contact_name`, `contact_email`, `contact_phone` fields
- Rich provider data stored in `source_payload` JSON (but currently `defer()`ed in list queries — not loaded)
- `mapBidToOffer()` in `store.ts` correctly maps `bid.contact_name` → `vendor_name`, `bid.seller?.name` → `vendor_company`, `bid.contact_email` → `vendor_email`

**Bug B9 — `source_payload` deferred in list queries:**
Rich vendor details (fleet, wifi, starlink, safety_certs) stored in `source_payload` are `defer()`ed when loading rows with bids. This means on page reload, the vendor detail panel won't show fleet/wifi/starlink info.

For the demo this is acceptable — the VendorContactModal doesn't use these fields. But for future: remove `defer(Bid.source_payload)` or add a detail endpoint.

### 3.6 Send Order (Tim's Request)

Tim wants to send to "all others first, then JetRight last once we know it's working."

**Current state:** No send ordering. When user clicks "Open Email App" on each tile, it opens their local mail client. This is manual per-vendor — user controls order.

**For demo:** This is fine. Tim clicks on each vendor tile in order. JetRight tile last.

**Future:** Batch send with priority ordering.

---

## 4. Design Principle: Category-Agnostic

All changes MUST work for any service category, not just private aviation. The demo is aviation but the platform serves roofing, HVAC, yacht charters, catering, etc.

- **Field names:** Use generic keys (`from`, `to`, `date`, `passengers`, `trip_type`) — never `departure_airport` in the modal schema
- **Templates:** The modal body template should be driven by `service_category` from the row, not hardcoded to aviation. The LLM already classifies the category — use it
- **Round-trip:** "One-way vs round-trip" applies to any transport service. Label it generically
- **Passenger names → Attendee/party names:** Works for catering headcounts, wedding parties, etc.
- **Reply-to email:** Universal — applies to every outreach

If something MUST be aviation-specific for the demo (e.g., "Wheels up" label, fleet/tail terminology in the email), gate it on `service_category === 'private_aviation'` rather than baking it into the generic path.

---

## 5. Requirements

### R1 — Add Missing Vendor (brett.driscoll2@gmail.com)
Add Brett Driscoll to `VENDORS["private_aviation"]` in `vendors.py`.

### R1b — Bump Vendor Endpoint Limit
The `/outreach/vendors/{category}` endpoint defaults to `limit=10`, but we now have 12 aviation vendors. Bump to `limit=15` (or remove cap) so all vendors appear as tiles.

### R2 — Fix Modal Width & Textarea Size
- Change `max-w-md` → `max-w-2xl` (672px) in `VendorContactModal.tsx`
- Change email body textarea `rows={6}` → `rows={14}`
- Change notes textarea `rows={2}` → `rows={3}`
- Make modal body scrollable (`max-h-[85vh] overflow-y-auto`)

### R3 — Fix "Wheels Up" Time Extraction
In `VendorContactModal.tsx`, add fallback keys to time extraction:
```
extract('wheels_up', 'wheels_up_time', 'departure_time', 'time', 'wheels_up_time_leg1')
```

### R4 — Round-Trip / Multi-Leg Support in Modal (Category-Agnostic)
- **Prerequisite:** Pass `row.service_category` as a new prop from `OfferTile` → `VendorContactModal` (currently not passed — blocks label switching)
- Add `trip_type` field (one-way / round-trip) — applies to any transport service (jets, yachts, car service)
- When round-trip: show return fields (return date, return time, return origin, return attendees)
- Use generic labels ("Origin", "Destination", "Attendees") — only swap to aviation-specific labels ("Departure Airport", "Passengers") when `service_category === 'private_aviation'`
- Update email body template to include both legs
- Pre-fill from constraints if available
- Canonical transport keys for prefill + templates: `from`, `to`, `date`, `time`, `attendees`, `trip_type`; return leg: `return_from`, `return_to`, `return_date`, `return_time`, `return_attendees` (accept aliases like `origin`, `destination`, `departure_date`, `wheels_up_time` via modal fallback map)

### R5 — Attendee / Party Names Field (Category-Agnostic)
- Add "Attendee names" textarea (label adapts: "Passenger names" for aviation, "Guest list" for catering, etc.)
- Per-leg for round-trip transport; single list for non-transport services
- Pre-fill from constraints (`passengers_outbound`, `passengers_return`, `passenger_names`, `return_passenger_names`, `attendees`, `return_attendees`, `guest_list`, `return_guest_list`)

### R6 — Reply-To Email Field
- Add "Replies to" input field in modal
- Pre-fill from user email or constraint
- Include in email body: `"Please send your quote to: {reply_to_email}"`

### R7 — Ensure Constraint→Factor Key Alignment
In BFF `generateAndSaveChoiceFactors()`:
- After generating factors, check each `choice_answers` key has a matching factor name
- If a constraint key (e.g., `origin`) doesn't match any factor name (e.g., `from_airport`), add a factor for it or remap the answer

### R8 — Update Email Body Template for Round-Trip (Category-Agnostic)
Default template adapts based on `service_category`. Aviation example below; other categories get simpler templates (roofing: address + scope + timeline; catering: date + headcount + venue).

**`mailto:` URL length warning:** Browser/OS `mailto:` links have URL length limits (~2000 chars on macOS, less on some platforms). If the rendered body exceeds ~1500 chars, the "Open Email App" button should fall back to copying subject+body to clipboard and prompting the user to paste into their email client manually. Add a visible "Copy to clipboard" fallback button.

Aviation default:
```
Hi {provider},

I'm reaching out on behalf of my client regarding a charter quote:

LEG 1 — OUTBOUND
Route: {from} → {to}
Date: {date}
Wheels up: {time} 
Passengers: {pax_outbound}
  {passenger_names_outbound}

LEG 2 — RETURN
Route: {return_from} → {return_to}
Date: {return_date}
Wheels up: {return_time}
Passengers: {pax_return}
  {passenger_names_return}

AIRCRAFT
Category: {aircraft_class}
Requirements: {requirements}

Please include in your quote:
• All-in price (incl. taxes, fuel, landing/handling, FBO, crew overnight)
• Tail number + operator (Part 135 certificate holder)
• Wi-Fi system type and whether Starlink is installed
• Cancellation/change policy
• Quote validity window

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}
```

Non-aviation example (catering):
```
Hi {provider},

We’re requesting a catering quote:
Date: {date}
Location: {location}
Headcount: {attendees}
Cuisine / dietary: {preferences}

Please send your quote to: {reply_to_email}

Thanks,
{persona_name}
{persona_role}
```

### R9 — Run Vendor Seed Script
After adding Brett Driscoll, run `seed_vendors.py` against prod DB to ensure all 12 vendors are in the `seller` table.

### R10 — Fix Business Jet Advisors Classification
Remove the "not a charter provider" caveat from `notes` field — or at minimum don't let it affect display. Tim wants them on the list.

### R11 — Bug Report Flow Triage (Tim saw an error)
- Reproduce the "report a bug" error Tim encountered
- If broken, fix or hide the entry point for the demo to avoid derailment

---

## 6. Non-Requirements (Defer)

- **Automated batch email send** — Tim will manually open each email via modal
- **Quote response tracking** — Quotes come back to Tim's email, not the platform
- **Vendor send ordering** — Tim controls this manually
- **Real email send via backend** — Using `mailto:` links (user's email client)
- **Multiple-row multi-leg** — Handle round-trip in a single row, not two rows

---

## 7. Test Plan

### Manual Click-Test (Demo Rehearsal)
1. Go to https://frontend-dev-aca4.up.railway.app
2. Chat: "I need a private jet charter, light jet with Wi-Fi, BNA to FWA, February 13, wheels up at 2pm central, 2 passengers"
3. **Verify:** Options card auto-fills with departure airport, arrival airport, date, wheels-up time, passengers — NO manual refresh needed
4. **Verify:** 11+ vendor tiles appear (including Brett Driscoll)
5. Click any vendor tile → "Request Quote" modal opens
6. **Verify:** Modal is wide enough to read the email body comfortably
7. **Verify:** Email body includes both legs (if round-trip filled in)
8. **Verify:** "Wheels up" time appears in the email body
9. **Verify:** Reply-to email field shows `tconnors@gmail.com`
10. Click "Open Email App" → verify mailto link opens with correct subject + body
11. Repeat for 2–3 vendors to confirm consistency
12. Click JetRight tile LAST

### Reload Test
1. After creating the row, hard-refresh the page
2. **Verify:** Vendor tiles re-appear (persisted as bids)
3. **Verify:** Options card shows the correct factors and answers
4. Click a vendor tile → modal shows correct data

---

## 8. Risk Matrix

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM doesn't extract "wheels up" from chat | HIGH | R3 + R7: fallback extraction + key alignment |
| Modal too small to display round-trip email | HIGH | R2: widen modal + taller textarea |
| Missing vendor (Brett Driscoll) | MEDIUM | R1: add to vendors.py |
| Constraint keys don't match factor names | HIGH | R7: post-generation alignment check |
| Email body doesn't include both legs | HIGH | R4 + R8: round-trip template |
| Bug report flow error (Tim reported) | MEDIUM | R11: triage + fix or hide for demo |
| Vendor endpoint caps at 10 (we have 12) | MEDIUM | R1b: bump limit to 15 |
| `mailto:` body truncation on long templates | MEDIUM | R8: clipboard fallback for long bodies |
| Modal lacks `service_category` prop | MEDIUM | R4 prerequisite: pass from OfferTile |
| Page reload loses vendor tiles | LOW | Already fixed (bids persist) |
| LLM generates generic fallback factors | LOW | RequestTile auto-regenerates |

---

## 9. Implementation Order

1. **R1** — Add Brett Driscoll vendor (5 min)
2. **R1b** — Bump vendor endpoint limit (2 min)
3. **R10** — Fix Business Jet Advisors notes (2 min)
3. **R2** — Widen modal + taller textarea (10 min)
4. **R3** — Fix time extraction (5 min)
5. **R5** — Add passenger names field (15 min)
6. **R6** — Add reply-to email field (10 min)
7. **R4 + R8** — Round-trip support + template (45 min)
8. **R7** — Constraint→factor key alignment (20 min)
9. **R9** — Run seed script (5 min)
10. **R11** — Bug report flow triage (10 min)
11. **Deploy + test** (15 min)

**Total estimate:** ~2.5 hours

---

## 10. Files to Modify

| File | Changes |
|------|---------|
| `apps/backend/services/vendors.py` | R1: Add Brett Driscoll. R10: Fix BJA notes |
| `apps/backend/routes/outreach.py` | R1b: Bump vendor endpoint default limit to 15 |
| `apps/frontend/app/components/OfferTile.tsx` | R4: Pass `service_category` prop to VendorContactModal |
| `apps/frontend/app/components/VendorContactModal.tsx` | R2, R3, R4, R5, R6, R8: Modal sizing, round-trip, time extraction, passenger names, reply-to, template |
| `apps/bff/src/llm.ts` | R7: Post-generation factor-key alignment in `generateAndSaveChoiceFactors()` |
| `apps/backend/scripts/seed_vendors.py` | R9: Run after vendor data update |
| `apps/frontend/app/components/ReportBugModal.tsx` (or equivalent) | R11: Triage bug report error (exact file TBD) |
