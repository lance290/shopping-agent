# PRD-01: Minor Dead Code Cleanup

**Priority:** P2 — small, zero risk  
**Effort:** 0.5 day  
**Dependencies:** None  
**Net effect:** Remove 2 unused models (~100 lines) and wire up services that are built but disconnected

---

## Context

The original audit flagged many features as "dead code." On review, nearly all of them are **revenue infrastructure** from the vision doc — contracts, Stripe Connect, signals, fraud detection, notifications, seller portal, checkout. These all stay.

What's actually dead is very small:

---

## What to Delete

### Models (in `models.py`, ~100 lines)

| Model | Why Delete |
|---|---|
| `AuditLog` | Never written to anywhere in the codebase. No route, no service, no import references it beyond the model definition. True dead code. |
| `ShareSearchEvent` | Tracks when shared links trigger searches. No code ever creates a `ShareSearchEvent` record. The `ShareLink` model's `search_initiated_count` / `search_success_count` columns are also never incremented. |

### Approach

- Remove the two model classes from `models.py`
- Remove any relationship references to them from other models
- Leave the DB tables in place (empty, inert) — no migration needed
- Or optionally create a migration: `alembic revision --autogenerate -m "drop_unused_auditlog_sharesearchevent"`

---

## What to Wire Up (not delete)

These services are built and correct but disconnected. They should be **connected**, not removed:

| Service | Status | What's Needed |
|---|---|---|
| `services/reputation.py` | Built, never called | Wire `update_merchant_reputation()` into seller quote submission and purchase completion flows |
| `services/fraud.py` | Built, in-memory only | Already wired into `clickout.py`. Upgrade storage from in-memory dict → Redis when Redis is added. Works correctly for single-process dev. |
| `services/notify.py` | Built, creates records | Already wired into `rows.py`. Needs a delivery mechanism (email via SES/Resend, or websocket push, or polling from frontend). Records accumulate correctly. |
| `services/outreach_monitor.py` | Built, never called | Wire into a cron/scheduled task to check for expired outreach and trigger follow-ups. |

**These are out of scope for this PRD** — they're noted here to track as future work, not as deletions.

---

## Verification

1. `cd apps/backend && python -c "from models import *; print('Models OK')"` — models import clean
2. `cd apps/backend && python -m pytest tests/ -x` — all tests pass
3. `grep -r "AuditLog\|ShareSearchEvent" apps/backend/` — only migration files reference them
