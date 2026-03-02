# PRD: Vendor Unresponsiveness Handling

**Status:** Partial — non-compliant (tracking exists, no timeout/escaplation)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** Expanded PRD ("BuyAnything.ai AI-Agent Facilitated Multi-Category Marketplace"), Edge Cases section — "Vendor unresponsive to outreach: The agent must notify the buyer after 24 hours and suggest alternative high-intent matches."

---

## Problem Statement

When BuyAnything.ai sends outreach to a vendor via WattData/email, there is **no timeout or follow-up mechanism**. If a vendor never responds:

- The buyer sees a stale "outreach sent" status indefinitely
- No alternatives are suggested
- The marketplace loop stalls silently
- Buyer trust erodes ("I submitted an RFP and nothing happened")

The outreach system tracks outbound vendor emails and engagement events, but has no concept of **expiry, escalation, or fallback**.

**Current state (incomplete):**
- Outreach events are stored with timestamps (sent/opened/clicked), but no timeout/expired state.
- No background job, follow-up email, or buyer notification flow exists.

---

## Requirements

### R1: Outreach Timeout Detection (P1)

Automatically detect when a vendor hasn't responded within a configurable window.

**Default timeout:** 24 hours after outreach `delivered` status (configurable per category).

**Acceptance criteria:**
- [ ] Background job runs every hour, checks for overdue outreach
- [ ] Outreach status transitions: `delivered` → `expired` after timeout
- [ ] Timeout configurable per service category (e.g., private aviation = 48h, HVAC = 24h)
- [ ] `OutreachEvent.expired_at` timestamp recorded

### R2: Buyer Notification on Timeout (P1)

Notify the buyer when a vendor hasn't responded.

**Notification channels (in priority order):**
1. In-app badge on the affected row (e.g., "1 vendor didn't respond")
2. Email digest (daily summary of expired outreach across all rows)

**Notification content:**
- Which vendor(s) didn't respond
- How long it's been
- CTA: "View alternatives" or "Re-send to more vendors"

**Acceptance criteria:**
- [ ] In-app notification appears on the row within 1 hour of timeout
- [ ] Email sent if buyer has email notifications enabled
- [ ] Notification links directly to the affected row

### R3: Automatic Alternative Suggestion (P2)

When outreach expires, proactively suggest alternatives.

**Strategy:**
1. **Re-search:** Trigger a new vendor discovery search for the same category/area
2. **Expand radius:** If the original outreach was geographically scoped, widen the search area
3. **Suggest registered merchants:** Check the Merchant Registry for matching categories
4. **Fall back to marketplace results:** Show product-based results if no service vendors respond

**Acceptance criteria:**
- [ ] On timeout, system auto-searches for alternative vendors
- [ ] New results appear as tiles in the buyer's row with a "Suggested alternative" badge
- [ ] Buyer can dismiss alternatives or send new outreach

### R4: Vendor Follow-Up (P2)

Before marking as expired, send one follow-up.

**Flow:**
1. After 12h with no response → Send follow-up email: _"Just checking in — [Buyer] is still looking for [service]. Reply to submit a quote."_
2. After 24h total → Mark as expired, notify buyer

**Acceptance criteria:**
- [ ] Follow-up email sent automatically at the halfway point
- [ ] `OutreachEvent.followup_sent_at` timestamp recorded
- [ ] Follow-up uses the same magic link as original outreach
- [ ] No more than 1 follow-up per outreach (avoid spam)

### R5: Outreach Health Metrics (P3)

Track vendor responsiveness at the aggregate level.

**Metrics:**
- Response rate by category (% of outreach that get a response)
- Average response time by category
- Expiry rate (% of outreach that timeout)
- Follow-up effectiveness (% of follow-ups that convert to response)

**Acceptance criteria:**
- [ ] Metrics available in `/admin/metrics` (see `09-analytics-success-metrics.md`)
- [ ] Categories with <20% response rate flagged for review
- [ ] Metrics inform default timeout values per category

---

## Technical Implementation

### Backend

**Models to modify:**
- `OutreachEvent` — Add `expired_at`, `followup_sent_at`, `timeout_hours`

**New files:**
- `apps/backend/services/outreach_monitor.py` — Background job for timeout detection + follow-up

**Modified files:**
- `apps/backend/routes/outreach.py` — Add status transition logic
- `apps/backend/routes/admin.py` — Add outreach health metrics

**Background job pattern:**
```python
async def check_expired_outreach():
    """Run every hour via scheduler or cron."""
    now = datetime.utcnow()
    
    # Find overdue outreach
    overdue = await session.exec(
        select(OutreachEvent)
        .where(OutreachEvent.status == 'delivered')
        .where(OutreachEvent.created_at < now - timedelta(hours=24))
        .where(OutreachEvent.expired_at.is_(None))
    )
    
    for event in overdue:
        event.status = 'expired'
        event.expired_at = now
        # Trigger buyer notification
        await notify_buyer_outreach_expired(event)
        # Trigger alternative search
        await suggest_alternatives(event.row_id)
```

**Scheduler options:**
- APScheduler (lightweight, in-process)
- Celery beat (if scaling needed)
- Railway cron job (external trigger)

### Frontend

- Row-level badge: "1 vendor didn't respond — View alternatives"
- Notification bell / inbox for outreach updates
- "Suggested alternative" badge on auto-discovered tiles

### Email

- Follow-up email template (SendGrid/Resend)
- Buyer notification email template

---

## Dependencies

- `03-multi-channel-sourcing-outreach.md` — Outreach system must exist (✅ done)
- `prd-merchant-registry.md` — Merchant Registry for alternative suggestions (✅ done)
- `04-seller-tiles-quote-intake.md` — Notification system gap (noted in GAP-ANALYSIS)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Follow-up emails flagged as spam | Use verified sender, respect unsubscribe, limit to 1 follow-up |
| Alternative suggestions are low quality | Only suggest if alternatives score above threshold |
| Background job missed/delayed | Idempotent design — re-running is safe; add health check |

---

## Effort Estimate

- **R1:** Small (half-day — status transition + background job skeleton)
- **R2:** Medium (1 day — notification system integration)
- **R3:** Medium (1 day — alternative search trigger)
- **R4:** Small (half-day — follow-up email template + scheduling)
- **R5:** Small (fold into analytics PRD)
