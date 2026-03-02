# PRD: Affiliate Disclosure UI

**Status:** Partial — non-compliant (missing required surfaces)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P0 — Legal/compliance requirement from original PRD  
**Origin:** `PRD-buyanything.md` Section 6.4 ("Disclosure")

---

## Problem Statement

The original PRD (`PRD-buyanything.md`, Section 6.4) established a **non-negotiable rule**: every commerce surface must include affiliate disclosure text. The FTC requires clear and conspicuous disclosure when affiliate links are used. BuyAnything.ai has affiliate handlers coded (`affiliate.py`) and clickout tracking active (`routes/clickout.py`), but disclosure is **incomplete and not present on all commerce surfaces**.

**Current state (incomplete):**
- Board header includes a short disclosure line, but only on the main board view.  
- A standalone disclosure page exists, but it does not satisfy in-context disclosure requirements.

This is a compliance risk that grows linearly with traffic and revenue.

---

## Requirements

### R1: Board-Level Disclosure (P0)

Display a persistent, unobtrusive disclosure on the procurement board wherever offer tiles are shown.

**Text:** _"We may earn a commission from qualifying purchases."_

**Placement options (choose one):**
- Footer of the tiles pane (below offer tiles)
- Subtle inline text above the first offer tile per row
- Tooltip on a small "ℹ️" icon next to "Results"

**Acceptance criteria:**
- [ ] Disclosure is visible on every page that shows offer tiles
- [ ] Disclosure text is readable (sufficient contrast, min 11px)
- [ ] Disclosure does not interfere with tile interaction (click, scroll)
- [ ] Disclosure is present on shared/public views (`ShareLink` pages)

### R2: Clickout-Level Disclosure (P1)

When a user hovers or long-presses on an offer tile's outbound link, show additional context.

**Acceptance criteria:**
- [ ] Tooltip or subtitle on offer tile link area: _"Opens merchant site. We may earn a commission."_
- [ ] Only shown on tiles where `click_url` routes through affiliate handler (not `NoAffiliateHandler`)

### R3: Disclosure on Merchant Register Page (P1)

Sellers registering through the merchant portal should understand the commission model.

**Acceptance criteria:**
- [ ] Registration form includes: _"BuyAnything.ai may earn a referral fee when buyers purchase through our platform."_
- [ ] Visible before form submission (not buried in terms)

### R4: Disclosure in Email Outreach (P2)

WattData outreach emails to vendors should include platform disclosure.

**Acceptance criteria:**
- [ ] Outreach email templates include a footer line about the platform's affiliate/commission model
- [ ] Compliant with CAN-SPAM requirements

---

## Technical Implementation

### Frontend Changes

**Files to modify:**
- `apps/frontend/app/components/Board.tsx` — Add disclosure below tiles pane
- `apps/frontend/app/components/OfferTile.tsx` — Optional tooltip on link hover
- `apps/frontend/app/merchants/register/page.tsx` — Add disclosure text above submit
- `apps/frontend/app/share/[token]/page.tsx` — Add disclosure on shared views

**Implementation pattern:**
```tsx
// Reusable component
function AffiliateDisclosure({ className }: { className?: string }) {
  return (
    <p className={cn("text-xs text-ink-muted", className)}>
      We may earn a commission from qualifying purchases.
    </p>
  );
}
```

### Backend Changes
- None required — this is a frontend-only feature.

### BFF Changes
- None required.

---

## Success Metrics

- **Coverage:** 100% of pages showing offer tiles include disclosure
- **Compliance:** Passes FTC affiliate disclosure guidelines review
- **UX impact:** Disclosure does not reduce offer CTR by more than 2%

---

## Risks

| Risk | Mitigation |
|------|------------|
| Disclosure reduces trust / CTR | Use subtle, standard language; A/B test placement |
| Missing on new surfaces | Add to component library; lint rule or PR checklist |
| International compliance varies | Start with FTC (US); add EU/UK variants as needed |

---

## Effort Estimate

**Small** — 1-2 hours for R1, half-day for R1-R3 complete.

---

## Dependencies

- None — can be implemented immediately.
- Pairs naturally with `00-revenue-monetization.md` (affiliate tags must be configured for disclosure to be meaningful).
