# Autonomous Outreach for a Web App

> Inspired by [OpenClaw](https://github.com/openclaw/openclaw) — see `docs/OpenClaw_Analysis.md`
> Last updated: 2026-02-14

---

## The Core Problem

We don't control the vendor contact channel. Every vendor is different:

- Some have web forms
- Some are email-only
- Some want phone calls
- Some use WhatsApp or Telegram
- Some have a QR code that opens a chat
- Some want you to "apply" through a portal
- Some just have an address and a phone number on a business card

**We will not know the contact method ahead of time.** It varies by vendor, by category, by country. A private jet broker in New York wants email. A diamond dealer in Antwerp wants WhatsApp. A renovation architect in Malibu wants a phone call. A yacht broker in Monaco wants you to fill out a form on their website.

The contact method is **data we need to discover and store per vendor**, not something we can assume or standardize.

---

## The Current Pain (real, from the private jet project)

The EA's actual workflow today:

1. Client says "I need a jet from Teterboro to Aspen on March 15"
2. Shopping Agent surfaces 11 charter providers
3. For each vendor, the EA has to figure out: *how do I even contact these people?*
4. EA sends 11 individual emails (the most common case)
5. EA tracks which vendors replied, which didn't, which quoted what
6. EA compares quotes manually (spreadsheet, notes, memory)
7. EA goes back and forth negotiating with 2-3 finalists
8. EA reports best option to client

**Steps 3-7 are the pain.** Sending, tracking, comparing, following up. All manual. All tedious. All error-prone.

---

## The Vision: Agent-Drafted, EA-Approved

The key insight: **the agent drafts, the EA proofreads and approves.** The EA stays in the loop but the grunt work disappears.

We don't need to know the contact method to start helping. We start with what we *can* control (drafting outbound messages), and progressively learn vendor preferences over time.

```
Client request comes in
        │
        ▼
  Shopping Agent finds vendors
        │
        ▼
  For each vendor, agent drafts an outreach message:
  ┌─────────────────────────────────────────────┐
  │ To: TurnKey Jets (sales@turnkeyjets.com)    │
  │                                             │
  │ Hi — we're looking for a light jet charter  │
  │ from Teterboro (TEB) to Aspen (ASE) on      │
  │ March 15, 2026 for 4 passengers. Could you  │
  │ provide availability and pricing?            │
  │                                             │
  │ Preferred aircraft: Citation CJ3+ or similar│
  │ Return: March 19, flexible on time          │
  │                                             │
  │ Best regards,                               │
  │ Sarah Chen                                  │
  │ Executive Assistant                         │
  └─────────────────────────────────────────────┘
        │
        ▼
  EA sees an "Outreach Queue" in the app:
  ┌──────────────┬──────────────┬─────────────────────────────┐
  │ Vendor       │ Method       │ Actions                     │
  ├──────────────┼──────────────┼─────────────────────────────┤
  │ TurnKey Jets │ 📧 Email     │ [Preview] [Edit] [Approve]  │
  │ NetJets      │ 📧 Email     │ [Preview] [Edit] [Approve]  │
  │ Wheels Up    │ 🌐 Web Form  │ [Preview] [Edit] [Approve]  │
  │ VistaJet     │ 📱 WhatsApp  │ [Copy to Clipboard]         │
  │ Flexjet      │ 📞 Phone     │ [View Talking Points]       │
  └──────────────┴──────────────┴─────────────────────────────┘
  [Approve All Emails]  [Pause All]
```

### What the EA does:
- **Email vendors**: Review draft → one-click approve → agent sends
- **Web form vendors**: Review pre-filled data → one-click approve → agent submits server-side
- **WhatsApp/Telegram vendors**: Review draft → copy to clipboard → EA pastes into their own chat
- **Phone vendors**: Review talking points → EA makes the call themselves

The agent handles what it can automate. The EA handles what requires a human touch. **Nothing goes out without EA eyes on it.**

---

## Three Levels (build incrementally)

### Level 1: "Draft & Send" (start here)

**What the agent does:**
- Drafts personalized outreach messages per vendor using request details
- Knows (or discovers) each vendor's preferred contact method
- Sends emails directly when EA approves
- For non-email channels, prepares the message for the EA to send manually

**What the EA does:**
- Reviews and edits drafts (proofreading, tone, adding personal touches)
- Approves outbound emails with one click
- Handles phone calls and manual channels with agent-prepared talking points

**What we need:**
- Outbound email sending (SendGrid, Postmark, or AWS SES)
- Outreach queue UI (draft → review → approve → sent)
- Per-vendor contact method stored in vendor profile
- LLM prompt that drafts professional outreach per category

**This alone is transformative.** The EA goes from writing 11 emails from scratch to reviewing 11 pre-written emails and clicking "Approve."

---

### Level 2: "Track & Compare" (the inbox)

**What the agent does:**
- Each request gets a dedicated reply-to address (e.g., `jet-7f3a@quotes.shoppingagent.com`)
- Vendor email replies flow into the app automatically
- LLM extracts structured data from replies (price, availability, terms)
- Builds a live comparison table
- Flags vendors who haven't replied and drafts follow-ups

**What the EA does:**
- Views all responses in one place (no inbox hunting)
- Manually logs responses from non-email channels (phone call notes, WhatsApp quotes)
- Reviews the comparison table
- Approves follow-up emails to non-responsive vendors

```
  EA sees a live tracking dashboard:
  ┌──────────────┬──────────┬──────────┬──────────┬───────────────┐
  │ Vendor       │ Price    │ Aircraft │ Status   │ Actions       │
  ├──────────────┼──────────┼──────────┼──────────┼───────────────┤
  │ TurnKey Jets │ $42,000  │ Citation │ ✅ Quoted │ [View Thread] │
  │ NetJets      │ $38,500  │ Phenom   │ ✅ Quoted │ [View Thread] │
  │ Wheels Up    │ —        │ —        │ ⏳ Sent   │ [Follow Up]   │
  │ VistaJet     │ $45,000  │ Global   │ ✅ Quoted │ [Logged by EA]│
  │ Flexjet      │ —        │ —        │ 📞 Called │ [Add Notes]   │
  └──────────────┴──────────┴──────────┴──────────┴───────────────┘
  Best deal: NetJets at $38,500 (Phenom 300)
```

**Key insight: the EA can manually log non-email responses.** The comparison table works regardless of contact channel because the EA fills in the gaps for phone/WhatsApp/in-person quotes.

**What we need:**
- Inbound email processing (SendGrid Inbound Parse, Postmark, or AWS SES)
- A mail domain (e.g., `quotes.shoppingagent.com`)
- LLM extraction pipeline (email text → structured quote data)
- Manual entry UI for EA to log phone/WhatsApp/other channel responses
- Follow-up draft generation for non-responsive vendors
- Notification system (in-app + email to EA)

---

### Level 3: "Negotiate" (EA-supervised)

**What the agent does:**
- Once quotes are in, drafts negotiation responses
- Uses competitive pricing data: "You quoted $42k but we have a $38.5k offer"
- Category-specific negotiation knowledge (e.g., "ask about empty leg availability")
- Drafts counter-offers and follow-ups

**What the EA does:**
- **Always proofreads before sending** — negotiation is high-stakes, tone matters
- Edits drafts to add personal knowledge or relationship context
- Decides negotiation strategy (which vendors to push, when to stop)
- Makes final recommendation to client

**Two modes:**

1. **Supervised** (default, recommended): Agent drafts every negotiation email. EA reviews, edits, approves. Nothing sends without a human click.
2. **Semi-autonomous** (opt-in, later): EA sets guardrails ("target below $35k", "max 2 rounds"). Agent executes within those bounds, reports results. EA can pause anytime.

---

## What We Don't Know Yet

Honest unknowns that will only become clear as we expand to new categories:

- **Diamond dealers**: Email? WhatsApp? In-person only? Referral-based?
- **Renovation contractors**: Web form? Phone? Site visit required first?
- **Yacht brokers**: Email? Broker network? Marina-specific protocols?
- **Art dealers**: Gallery contact? Auction house? Private introduction only?
- **Wine/spirits**: Distributor email? Allocation lists? Club membership?

**The system must be flexible enough to handle any contact method.** The vendor profile stores what we know. The EA fills in what we don't. Over time, our vendor data gets richer.

---

## The EA's Life (the north star)

The EA's experience should feel like this:

| Before Shopping Agent | After Shopping Agent |
|---|---|
| Research vendors manually | Agent finds and ranks vendors |
| Figure out how to contact each one | Agent knows (or discovers) contact method |
| Write 11 emails from scratch | Review 11 pre-written emails, click Approve |
| Track responses in email + spreadsheet | All responses in one dashboard |
| Manually compare quotes | Agent builds comparison table |
| Draft negotiation emails | Agent drafts, EA proofreads and sends |
| Report to client via email | Share link with live status |

**The EA goes from doing everything to reviewing everything.** The thinking and typing are done. The judgment and relationships remain theirs.

---

## Safety Model (learning from OpenClaw's horror stories)

### Rate Limits
- Max 20 vendor contacts per request
- Max 3 follow-ups per vendor
- Max 3 negotiation rounds per vendor

### EA Always in the Loop
- Every outbound email requires EA approval (Level 1 & 2)
- Negotiation drafts always require EA review (Level 3 supervised)
- Semi-autonomous mode is opt-in and has hard budget limits

### Action Budgets
- Each request gets a visible "budget" of outbound actions
- "7 of 20 contacts used" — EA always knows the scope
- Budget exhaustion requires explicit EA action to extend

### Emergency Stop
- "Pause All Outreach" button on every request — one click, everything stops
- All queued emails held, all follow-ups paused
- Resumes only on explicit EA action

### Audit Trail
- Every outbound message logged with timestamp, content, recipient, and result
- Every inbound response logged and linked to the thread
- EA can review the full history of everything the agent did
- Client-shareable audit trail for transparency

---

## The Moat (grows with every request)

- **Vendor contact intelligence** — preferred contact method, best email, response time, who to ask for
- **Category-specific outreach templates** — "for jets, always include route, dates, pax count, aircraft preference"
- **Negotiation playbooks** — "for jets, ask about empty legs; for diamonds, ask about GIA markup vs. Rapaport"
- **Quote normalization** — comparing apples to apples across vendors with wildly different pricing structures
- **Vendor responsiveness scoring** — "TurnKey responds in 2 hours, Flexjet takes 3 days, VistaJet ghosts after first quote"
- **EA workflow patterns** — what types of edits EAs make to drafts tells us how to improve the drafts

This is a data flywheel. Every request makes the next one better.

---

## How This Compares to OpenClaw

| Capability | OpenClaw (local install) | Shopping Agent (web app) |
|---|---|---|
| Contact vendors | Browser + email + WhatsApp on user's machine | Agent drafts, EA approves/sends |
| Monitor responses | Gmail Pub/Sub on local gateway | Dedicated inbox + EA manual logging |
| Negotiate | LLM drafts, auto-sends | LLM drafts, EA proofreads and approves |
| Contact method | Assumes browser/email/messaging access | Discovers and stores per vendor; adapts |
| Kill switch | Stop the gateway | "Pause All" button in UI |
| Install required | Yes (Node, CLI, API keys) | No (just a browser) |
| Target user | Technical power users | HNWIs and their EAs |
| Human in loop | Optional | Required (by design) |

**We trade full autonomy for trust.** An HNWI's EA will never let a bot send emails unsupervised from their boss's account. But they'll happily review and approve 11 pre-written emails in 2 minutes instead of writing them from scratch in 45 minutes.
