# Bob Integration Guide — Shopping Agent Backend

## What Is Bob?

Bob is an AI family shopping agent that lives inside communication channels (email, SMS, WhatsApp). Users text or email things like "we need milk" and Bob:

1. Parses the message using the Shopping Agent's **Unified NLU Decision Engine** (`services.llm.make_unified_decision`)
2. Creates a `Row` inside a `Project` called "Family Shopping List"
3. Triggers **automated sourcing** across all existing search providers to populate `Bid`s
4. Replies to the user with results via **Resend** (email) or Twilio (SMS)

Bob adds **zero new models or databases**. It is a conversational adapter on top of the existing Shopping Agent core.

---

## Architecture Overview

```
                    ┌──────────────────┐
  Email to          │  Resend Inbound  │──► POST /bob/webhooks/resend
  bob@buyanything.ai│  Webhook (JSON)  │
                    └──────────────────┘
                    ┌──────────────────┐
  SMS to Bob's      │  Twilio Webhook  │──► POST /bob/webhooks/twilio
  phone number      │  (form-encoded)  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ process_bob_msg  │
                    │  1. Find User    │
                    │  2. Find/Create  │
                    │     Project      │
                    │  3. NLU Decision │  ◄── make_unified_decision()
                    │  4. Create Row   │  ◄── _create_row() / _update_row()
                    │  5. Source Bids  │  ◄── _stream_search()
                    │  6. Reply (Email)│  ◄── Resend send
                    └──────────────────┘
```

## Data Model Mapping (Bob → Shopping Agent)

| Bob Concept       | Shopping Agent Model | Notes |
|-------------------|---------------------|-------|
| Family Group      | `Project`           | Title = "Family Shopping List", one per user |
| List Item         | `Row`               | Created via `_create_row` with NLU-extracted title/constraints |
| Swap / Deal       | `Bid`               | Populated by existing sourcing providers |
| User / Member     | `User`              | Looked up by `email` (Resend) or `phone_number` (Twilio) |
| Brand / Vendor    | `Vendor`            | Existing vendor base — no new portal needed |

## Files Added / Modified

| File | Change |
|------|--------|
| `apps/backend/routes/bob.py` | **New.** Bob router with webhook endpoints and core processing logic |
| `apps/backend/main.py` | **Modified.** Added `bob_router` import and `app.include_router(bob_router)` |
| `docs/prd/bob-master-prd.md` | **New.** Bob master PRD |
| `docs/prd/bob-shopping-agent/` | **New.** 7 child PRDs + backlog + traceability matrix |

## Shared Services Used

- **`services.llm.make_unified_decision`** — NLU intent extraction (same engine as the chat UI)
- **`services.llm.generate_choice_factors`** — Choice factor generation for rows
- **`routes.chat._create_row`** / **`_update_row`** — Row CRUD
- **`routes.chat._save_factors_scoped`** — Persist choice factors
- **`routes.chat._stream_search`** — Multi-provider sourcing
- **`services.email`** — Resend email delivery (shared API key, dev intercept, etc.)

## Environment Variables

Add these to `.env` (or Railway env vars):

```bash
# Bob-specific
BOB_FROM_EMAIL=bob@buyanything.ai        # Outbound sender address
RESEND_WEBHOOK_SECRET=whsec_xxxxx        # From Resend dashboard → Webhooks → Signing secret
TWILIO_AUTH_TOKEN=xxxxxxxx               # From Twilio console
TWILIO_PHONE_NUMBER=+1234567890          # Bob's SMS number

# Already in use by Shopping Agent (no changes needed)
# RESEND_API_KEY=re_xxxxx
# FROM_EMAIL=noreply@buyanything.ai
# DEV_EMAIL_OVERRIDE=your-dev-email@...  (redirects all outbound in dev mode)
```

## Resend Setup

1. **Inbound domain:** In Resend dashboard, add an inbound domain for `buyanything.ai` (or whichever domain receives `bob@...` mail). Set the MX records as Resend instructs.
2. **Webhook endpoint:** Create a webhook in Resend pointing to:
   ```
   https://<your-backend-url>/bob/webhooks/resend
   ```
3. **Signing secret:** Copy the webhook signing secret into `RESEND_WEBHOOK_SECRET`.
4. **Outbound:** Bob replies use the same `RESEND_API_KEY` already configured. The sender is `Bob <bob@buyanything.ai>` (configurable via `BOB_FROM_EMAIL`).

## Twilio Setup

1. **Phone number:** Buy or use an existing Twilio number.
2. **Webhook URL:** In Twilio console → Phone Numbers → your number → Messaging → "A Message Comes In":
   ```
   https://<your-backend-url>/bob/webhooks/twilio   (HTTP POST)
   ```
3. **Auth token:** Copy from Twilio console into `TWILIO_AUTH_TOKEN`.
4. **User phone mapping:** Users must have `phone_number` set in the `user` table (E.164 format, e.g. `+14155551234`) for SMS lookup to work.

---

## How to Test

### Test 1: Email webhook (local, no Resend needed)

Simulate a Resend inbound webhook with curl. No signature verification if `RESEND_WEBHOOK_SECRET` is unset.

```bash
# Start the backend
cd apps/backend && uvicorn main:app --reload --port 8000

# Simulate inbound email (use an email that exists in your user table)
curl -X POST http://localhost:8000/bob/webhooks/resend \
  -H "Content-Type: application/json" \
  -d '{
    "from": "youruser@example.com",
    "to": "bob@buyanything.ai",
    "subject": "Grocery list",
    "text": "I need organic whole milk and sourdough bread"
  }'
```

**Expected:** `{"status": "accepted"}` and in the logs:
- `[Bob] Resend inbound from youruser@example.com: Grocery list`
- `[Bob] Decision: create_row - ...`
- `[Bob DEMO EMAIL] To: ...` (or `[Bob] Reply sent to ...` if Resend is configured)

**Verify in DB:**
```sql
SELECT p.id, p.title FROM project WHERE title = 'Family Shopping List';
SELECT r.id, r.title, r.status FROM row WHERE project_id = <project_id>;
SELECT b.id, b.item_title, b.price FROM bid WHERE row_id = <row_id> LIMIT 5;
```

### Test 2: SMS webhook (local, no Twilio needed)

```bash
# Simulate Twilio webhook (use a phone number that exists in your user table)
curl -X POST http://localhost:8000/bob/webhooks/twilio \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=%2B14155551234&Body=add%20eggs%20and%20butter&To=%2B19876543210"
```

**Expected:** XML response `<Response/>` and in the logs:
- `[Bob] Twilio SMS from +14155551234: add eggs and butter`
- Either processes the message (if phone is mapped to a user) or logs unknown phone.

### Test 3: End-to-end with ngrok

For real email/SMS testing through Resend and Twilio:

```bash
# Expose local backend
ngrok http 8000

# Use the ngrok URL as the webhook endpoint:
# Resend: https://xxxx.ngrok.io/bob/webhooks/resend
# Twilio: https://xxxx.ngrok.io/bob/webhooks/twilio
```

Then send a real email to `bob@buyanything.ai` or text Bob's Twilio number.

### Test 4: Verify NLU + Sourcing pipeline

After any of the above, confirm the full pipeline worked:

1. **Row created** — Check `row` table for a new entry with the parsed title
2. **Choice factors** — Check `choice_factor` table for the row
3. **Bids populated** — Check `bid` table for results from sourcing providers
4. **Outbound reply** — Check logs for `[Bob] Reply sent to ...` or `[Bob DEMO EMAIL]`

### Quick smoke test checklist

- [ ] `POST /bob/webhooks/resend` returns `200 {"status": "accepted"}`
- [ ] Known user email → `Project` created (or found) + `Row` created
- [ ] Unknown user email → sends onboarding email (or demo-logs it)
- [ ] `POST /bob/webhooks/twilio` returns `200` with XML `<Response/>`
- [ ] Known phone → maps to user email, processes, and replies via SMS
- [ ] Unknown phone → sends onboarding SMS (or demo-logs it)
- [ ] Outbound reply sent on same channel user used (email or SMS)
- [ ] `Row.chat_history` updated with user + assistant messages after processing
- [ ] `project_member` row created linking user to project with correct channel

---

## Implemented Features

### Onboarding (unknown users)
When an unknown email or phone contacts Bob, they receive a welcome message with a signup link:
- **Email:** `send_bob_onboarding_email()` sends via Resend
- **SMS:** `send_bob_onboarding_sms()` sends via Twilio

### Conversation History
Bob persists conversation history on `Row.chat_history` (JSON array of `{role, content}`):
- **`_load_chat_history(row)`** — loads prior messages before calling the NLU engine
- **`_append_chat_history(session, row, user_msg, assistant_msg)`** — appends after each exchange
- Capped at last 50 messages to prevent unbounded growth
- Compatible with the existing `parse_chat_history()` validator in `utils/json_utils.py`

### SMS Outbound Reply
Bob replies on the **same channel** the user used:
- **`send_bob_sms(to_phone, body_text)`** — sends via `twilio.rest.Client`
- Falls back to demo-logging when `TWILIO_ACCOUNT_SID` is unset
- SMS body truncated to 1600 chars (SMS limit)

### Family Group Sharing (`ProjectMember` table)
New model `ProjectMember` maps multiple users to a shared `Project`:
- **Columns:** `project_id`, `user_id`, `role` (owner/member), `channel` (email/sms/whatsapp), `invited_by`, `joined_at`
- **Unique index** on `(project_id, user_id)` prevents duplicates
- `_ensure_project_member()` auto-registers the user on every message, tracking their channel preference
- **Migration:** `alembic/versions/s07_add_project_member_table.py` (run `alembic upgrade head`)

### Additional env var needed for SMS outbound
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxx   # From Twilio console
```

## Remaining Future Work

- **Invite flow:** Let a household owner text Bob "invite mom@email.com" to add members
- **Multi-member routing:** When a Row gets new Bids, notify all ProjectMembers (not just the sender)
- **WhatsApp channel:** Add a `/bob/webhooks/whatsapp` endpoint (WhatsApp Business API)
- **Receipt OCR:** Image processing for receipt-based redemption (V3 milestone)
