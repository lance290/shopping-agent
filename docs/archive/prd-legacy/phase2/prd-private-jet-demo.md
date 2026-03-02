# PRD: Private Jet Demo (10-Day Sprint)

**Status:** Active Sprint  
**Target Date:** 2026-02-11 (Investor Pitch)  
**Created:** 2026-02-01

---

## Objective

Demonstrate the complete buyer-to-seller loop for a **private jet charter** use case:

> "I need a private jet trip" → LLM extracts choice factors → LLM suggests top vendors → outreach emails → vendor submits quote → buyer selects → email handoff to close

## Demo Script

### Act 1: Buyer Request
1. Buyer types: "I need a private jet from SF to Vegas for 6 people next Friday"
2. LLM extracts choice factors:
   - Origin: San Francisco (SFO/OAK)
   - Destination: Las Vegas (LAS)
   - Date: Next Friday (Feb 7, 2026)
   - Passengers: 6
   - Trip type: One-way / Round-trip?
3. System asks clarifying questions on right panel
4. Buyer answers: "Round trip, returning Sunday evening"

### Act 2: LLM Vendor Discovery
5. System: "Finding private jet providers..."
6. LLM suggests vendors: "For private jet charters, top providers include NetJets, Wheels Up, XO, VistaJet, and Flexjet. Let me reach out to them."
7. System queries WattData (mocked) for contact info
8. Outreach emails sent to 5 vendors
9. UI shows: "Contacted 5 vendors • Waiting for quotes"

### Act 3: Vendor Quote (Demo: Manual Trigger)
10. Vendor receives email with RFP summary
11. Vendor clicks magic link → Quote form
12. Vendor fills: $12,500 round-trip, Citation XLS, includes catering
13. Submit → Quote appears as tile in buyer's row

### Act 4: Selection & Close
14. Buyer reviews quote tile (shows price, aircraft, amenities)
15. Buyer clicks "Select"
16. Confirmation: "This will introduce you to XO via email. Continue?"
17. Buyer confirms → Introduction emails sent
18. UI shows: "Deal in progress • Introduced via email"
19. (Optional) Buyer marks "Closed" after booking

---

## What We Need to Build

### Must Have (Demo Critical)

| Component | Status | Effort | Notes |
|-----------|--------|--------|-------|
| **LLM Vendor Suggestion** | 🔲 | S | Add tool/prompt for "suggest vendors for category" |
| **Mock WattData Response** | 🔲 | S | Return hardcoded private jet vendors |
| **Outreach Email (basic)** | 🔲 | M | SendGrid + template + magic link |
| **Quote Intake Form** | 🔲 | M | Public form, no auth, basic fields |
| **Quote → Tile Display** | 🔲 | S | Quote appears as bid in row |
| **Select + Email Handoff** | 🔲 | M | Confirmation modal + intro emails |
| **Demo UI Polish** | 🔲 | S | "Contacting vendors" / "Waiting for quotes" states |

### Nice to Have (If Time)

| Component | Effort | Notes |
|-----------|--------|-------|
| Multiple quotes comparison | S | Side-by-side tiles |
| "Mark as Closed" tracking | S | Button + status update |
| Vendor notification of acceptance | S | Email to losing vendors |

### Out of Scope (Post-Demo)

- Real WattData MCP integration
- Merchant Registry (self-registration)
- Stripe/DocuSign closing
- Mobile optimization

---

## Technical Implementation

### 1. LLM Vendor Suggestion

Add to BFF chat flow:

```typescript
// When intent.category is "service" or "charter"
const vendorSuggestion = await llm.complete({
  prompt: `The user needs: ${intent.description}
  
  What are the top 5 vendors/providers for this type of service?
  Return as JSON: { "vendors": ["name1", "name2", ...], "category": "private_aviation" }`,
});
```

### 2. Mock WattData Integration

```typescript
// services/wattdata-mock.ts
const MOCK_VENDORS: Record<string, Vendor[]> = {
  "private_aviation": [
    { name: "NetJets", email: "demo+netjets@buyanything.ai", phone: "555-0101" },
    { name: "Wheels Up", email: "demo+wheelsup@buyanything.ai", phone: "555-0102" },
    { name: "XO", email: "demo+xo@buyanything.ai", phone: "555-0103" },
    { name: "VistaJet", email: "demo+vistajet@buyanything.ai", phone: "555-0104" },
    { name: "Flexjet", email: "demo+flexjet@buyanything.ai", phone: "555-0105" },
  ],
  // Add more categories as needed
};

export function getVendors(category: string): Vendor[] {
  return MOCK_VENDORS[category] || [];
}
```

### 3. Outreach Email

```
Subject: RFP: Private Jet Charter - SF to Vegas (Feb 7-9)

Hi [Vendor Name],

A buyer on BuyAnything is looking for a private jet charter:

📍 Route: San Francisco → Las Vegas (round-trip)
📅 Dates: Feb 7 - Feb 9, 2026
👥 Passengers: 6
💼 Type: Business/Leisure

To submit your quote, click here:
[Submit Quote] → https://app.buyanything.ai/quote/{magic_token}

This link expires in 48 hours.

—BuyAnything Team
```

### 4. Quote Intake Form

**URL:** `/quote/{token}`

**Fields:**
- Price (required)
- Currency (USD default)
- Aircraft type (text)
- Description / What's included
- Availability confirmation (checkbox)
- Contact name
- Contact phone

**On Submit:**
- Validate token
- Create SellerQuote record
- Convert to Bid (appears in buyer's row)
- Send notification to buyer

### 5. Email Handoff

**On "Select" click:**
1. Show confirmation modal with quote summary
2. On confirm:
   - Create DealHandoff record
   - Send buyer intro email (with vendor contact)
   - Send vendor notification (with buyer contact)
3. Update UI: "Introduced via email"

---

## 10-Day Sprint Schedule

### Days 1-2: Foundation
- [ ] Create `seller_quotes` table + migration
- [ ] Create `deal_handoffs` table + migration
- [ ] Set up SendGrid (or Postmark) integration
- [ ] Create magic link token generation

### Days 3-4: LLM + Outreach
- [ ] Add LLM vendor suggestion to BFF
- [ ] Create mock WattData service
- [ ] Build outreach email template
- [ ] Implement outreach trigger in chat flow

### Days 5-6: Quote Intake
- [ ] Build `/quote/{token}` page (Next.js)
- [ ] Quote submission API endpoint
- [ ] Quote → Bid conversion logic
- [ ] Buyer notification on new quote

### Days 7-8: Selection + Handoff
- [ ] Add "Select" button to quote tiles
- [ ] Confirmation modal component
- [ ] Email handoff implementation
- [ ] UI state updates ("Introduced via email")

### Days 9-10: Polish + Demo Prep
- [ ] End-to-end testing
- [ ] Demo script rehearsal
- [ ] Fix bugs
- [ ] Prepare fallback demo video (just in case)

---

## Demo Environment

- **URL:** https://demo.buyanything.ai (or localhost for in-person)
- **Test emails:** Use `demo+*@buyanything.ai` aliases
- **Pre-seeded data:** One complete flow already done (show history)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Email deliverability issues | Use verified sending domain; test early |
| LLM gives bad vendor suggestions | Hardcode fallback list for private jets |
| Quote form looks unpolished | Use shadcn/ui components; keep it simple |
| WattData MCP ships mid-sprint | Mock is thin wrapper; easy to swap |

---

## Success Criteria

**For the demo:**
- [ ] Buyer types request → sees "Contacting vendors" within 5s
- [ ] Outreach emails actually delivered (check inbox)
- [ ] Quote form works and submission appears as tile
- [ ] Select → Email handoff sends real emails
- [ ] Investor understands the value prop

**NOT required for demo:**
- Production-ready code
- Scalability
- Full error handling
- Mobile UI

---

## Post-Demo: What We'll Have

After this sprint, we'll have built:
1. **LLM vendor discovery** — reusable for any service category
2. **Quote intake system** — magic links, forms, bid conversion
3. **Email handoff** — MVP closing mechanism
4. **Outreach infrastructure** — SendGrid integration, templates

This becomes the foundation for the full Phase 2 seller loop.
