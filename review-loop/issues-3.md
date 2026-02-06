# Code Review Issues - Iteration 3 (Pass 2)

## Summary
- **Total Issues**: 4
- **Major**: 2 (should fix)
- **Minor**: 2 (nice to fix)

All Critical issues from Pass 1 remain fixed. Pass 2 found authorization and convention gaps.

## Major Issues 🟠

### M5: `close_handoff` authenticates but doesn't authorize — any user can close any handoff
- **File**: `apps/backend/routes/quotes.py:347-355`
- **Category**: Security / Authorization
- **Problem**: The endpoint checks the user is logged in (authn) but never checks that the user owns the handoff (authz). Any authenticated user who guesses a handoff_id integer can close someone else's deal. The `DealHandoff` model has `buyer_user_id` — should verify `handoff.buyer_user_id == auth_session.user_id`.
- **Fix**: Add `if handoff.buyer_user_id != auth_session.user_id: raise HTTPException(403)` after fetching the handoff.

### M6: `send_reminders` endpoint has no authentication — email spam vector
- **File**: `apps/backend/routes/outreach.py:396-447`
- **Category**: Security / Abuse
- **Problem**: `POST /outreach/rows/{row_id}/reminders` is unauthenticated. Anyone can trigger reminder emails to all vendors for any row. This is a spam/abuse vector.
- **Fix**: Add auth requirement. Only the row owner should be able to trigger reminders.

## Minor Issues 🟡

### m4: `quote/[token]/page.tsx` uses `catch (err: any)` instead of `catch (err: unknown)`
- **File**: `apps/frontend/app/quote/[token]/page.tsx:43,83`
- **Category**: Type Safety / Convention
- **Problem**: Other pages (share, merchants) correctly use `catch (err: unknown)` with `instanceof Error` check. This page uses `err: any` and directly accesses `err.message`, which will crash if the error isn't an Error object.
- **Fix**: Change to `catch (err: unknown)` + `err instanceof Error ? err.message : 'Failed'` pattern.

### m5: `handleShare` has empty catch that shows misleading success toast
- **File**: `apps/frontend/app/components/RowStrip.tsx:491-494`
- **Category**: UX / Error Handling
- **Problem**: The catch block on line 491 is empty, then line 494 shows `onToast?.('Share link ready.', 'success')` — user sees "success" even when sharing actually failed.
- **Fix**: Move the fallback toast inside the try block or show an error toast in the catch.

## Previously Fixed (Pass 1) — Verified ✅
| ID | Status |
|----|--------|
| C1 | ✅ `backend_url` defined in `send_outreach_email` |
| C2 | ✅ Merchant register proxied through `/api` |
| M1 | ✅ `close_handoff` has auth |
| M2 | ✅ Email removed from merchant search |
| M3 | ✅ `normalizeBaseUrl` extracted to `utils/bff.ts` |
| M4 | ✅ TODO added to merchant search |

## Verdict: FAIL (2 Major issues)

Fix M5 and M6, then re-verify.
