# PRD L7: Single-Player Mode (Procurement Tracker)

**Priority:** P3 — Post-launch
**Target:** Week 6–7 (Mar 15–28, 2026)
**Depends on:** Notification system (Phase 5 PRD 00), Tile detail panel (Phase 5 PRD 01)

---

## Problem

Two-sided marketplaces face the "chicken-and-egg" problem: buyers won't come without sellers, sellers won't come without buyers. The standard solution is **single-player mode** — build a product so valuable to one side that they use it even without the other side.

Examples:
- **Zillow** → Zestimate (standalone home value tool) → then marketplace
- **OpenTable** → Restaurant reservation management → then consumer booking
- **Yelp** → Business directory + reviews → then lead gen marketplace

BuyAnything currently requires sellers to be useful. Without them, a buyer searches and gets only Amazon/Google Shopping results — not differentiated from just searching Amazon directly.

---

## Solution: Personal Procurement Tracker

Make BuyAnything valuable **even without sellers** by being the best tool for organizing and comparing purchases.

### R1 — Purchase Project Board

A Trello/Notion-like board for tracking procurement across multiple categories:

```
┌─────────────┬──────────────┬─────────────┬──────────────┐
│  Researching │  Comparing   │  Decided    │  Purchased   │
├─────────────┼──────────────┼─────────────┼──────────────┤
│ New Roof     │ Office Chair │ Jet Charter │ HVAC Repair  │
│ Bicycle      │ Laptop       │             │              │
│              │ Printer      │             │              │
└─────────────┴──────────────┴─────────────┴──────────────┘
```

This is essentially the existing Projects + Rows but with a Kanban view and status tracking.

### R2 — Comparison Worksheets

For each Row, a structured comparison table:

| Factor | Option A (Amazon) | Option B (Best Buy) | Option C (Vendor Quote) |
|--------|------------------|--------------------|-----------------------|
| Price | $899 | $949 | $825 |
| Delivery | 2 days | 5 days | 3 days |
| Warranty | 1 year | 2 years | 1 year |
| Rating | 4.2★ | 4.5★ | N/A |

Data auto-populated from tiles/bids. User can add custom columns.

### R3 — Price Tracking & Alerts

For product purchases (Amazon, eBay):
- Track price over time per bid
- Alert when price drops below threshold
- "Best time to buy" recommendation

This leverages existing search infrastructure — just re-run searches periodically.

### R4 — Receipt & Invoice Organization

After purchase:
- Upload receipt/invoice image
- Auto-extract vendor, amount, date (OCR)
- Link to original Row/Bid
- Export for expense reports

### R5 — Collaborative Procurement

Share a project board with team members:
- Co-workers can vote on options
- Comments + @mentions
- Approval workflow for purchases > $X

This extends the existing ShareLink + collaboration features.

---

## Why This Works

1. **Standalone value** — A buyer uses the tracker even without sellers. It's better than spreadsheets.
2. **Natural upgrade** — "You've been comparing laptops for 3 days. Want us to find you a deal?" → triggers marketplace.
3. **Data generation** — Every tracked purchase teaches the AI about buyer preferences.
4. **Retention** — Users return to check their board, update statuses, track prices.
5. **Virality** — "Share this comparison with your team" drives collaborative sign-ups.

---

## Acceptance Criteria

- [ ] Kanban-style project board with 4 status columns
- [ ] Drag-and-drop between columns
- [ ] Comparison worksheet auto-populated from tiles
- [ ] At least price tracking for Amazon products (re-search on schedule)
- [ ] Board shareable via existing ShareLink mechanism
- [ ] Works on mobile (responsive cards, not table)
