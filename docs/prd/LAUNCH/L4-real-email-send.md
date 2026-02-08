# PRD L4: Real Email Send & Deliverability

**Priority:** P0 — Pre-launch
**Target:** Week 1 (Feb 10–14, 2026)
**Depends on:** Custom domain (D1), Email provider API key (E1)

---

## Problem

The platform currently uses `mailto:` links for vendor outreach. This means:

1. **No emails are actually sent from the platform** — the user's local email client opens
2. **Zero tracking** — can't measure open rates, click rates, or response rates
3. **No automated follow-ups** — outreach_monitor.py can't send reminders
4. **Unprofessional** — vendor sees the email from `tconnors@gmail.com`, not `quotes@buyanything.ai`
5. **URL length limits** — `mailto:` breaks on long email bodies (>2000 chars)

The backend code for email sending already exists in `apps/backend/services/email.py` using Resend, but it's not wired to real sending in the outreach flow.

---

## Solution

### R1 — Email Provider Setup (Day 1)

1. Sign up for Resend (or SendGrid — Resend preferred for simplicity)
2. Verify custom domain (`buyanything.ai`) in provider dashboard
3. Set up SPF, DKIM, DMARC DNS records
4. Set `RESEND_API_KEY` env var in Railway
5. Verify: send test email → check headers for "pass" on SPF/DKIM

### R2 — Wire Outreach to Real Send (Day 2)

Currently `routes/outreach.py` has the outreach trigger but uses mock/mailto. Change to:

1. When buyer clicks "Send Quote Request" on a vendor tile:
   - Call `services/email.py::send_outreach_email()` with real Resend API
   - Email sent **from** `quotes@buyanything.ai`
   - **Reply-to** set to buyer's email address
   - Track `OutreachEvent` with `status=sent`, `message_id` from Resend

2. Set up Resend webhook for delivery events:
   - `delivered` → update OutreachEvent status
   - `bounced` → update OutreachEvent status, flag vendor email
   - `opened` → update OutreachEvent, log timestamp
   - `clicked` → update OutreachEvent (if email contains links)

### R3 — Transactional Email Templates (Day 3)

Create HTML email templates for:

| Template | Trigger | Content |
|----------|---------|---------|
| **Quote Request** | Buyer contacts vendor | Itinerary details, requirements, reply-to buyer |
| **Quote Received** | Vendor submits quote via platform | "You received a quote from [Vendor]" to buyer |
| **Welcome** | New user sign-up | "Welcome to BuyAnything.ai" + first steps |
| **RFP Match** | New buyer RFP matches seller category | "[Buyer] needs [Category] — submit a quote" to seller |
| **Outreach Reminder** | 48h no response from vendor | Follow-up to vendor |
| **Deal Selected** | Buyer selects a quote/bid | Notification to vendor that they were chosen |

All templates should:
- Be responsive (mobile-readable)
- Include unsubscribe link (CAN-SPAM)
- Use platform branding
- Have plain-text fallback

### R4 — Follow-Up Automation (Day 4)

Wire `services/outreach_monitor.py` to actually send follow-ups:

1. Cron job (or scheduled task) runs every 6 hours
2. Finds `OutreachEvent` records where `status=sent` and `created_at > 48h ago` and `followup_sent_at IS NULL`
3. Sends follow-up email via Resend
4. Updates `followup_sent_at` timestamp
5. After 2nd follow-up with no response, marks as `expired`

### R5 — Sending Reputation Warmup

New domain = cold sender reputation. Plan:

- Week 1: Max 50 emails/day (Tim's demo + internal testing)
- Week 2: Max 200 emails/day
- Week 3: Max 500 emails/day
- Monitor bounce rate (must stay < 2%) and spam complaints (< 0.1%)

---

## Acceptance Criteria

- [ ] Emails sent from `quotes@buyanything.ai` (or similar branded address)
- [ ] Reply-to set to buyer's actual email
- [ ] Delivery status tracked in `OutreachEvent`
- [ ] At least SPF + DKIM passing on sent emails
- [ ] Unsubscribe link in every email
- [ ] Follow-up automation sends after 48h no response
- [ ] HTML templates render correctly in Gmail, Apple Mail, Outlook
