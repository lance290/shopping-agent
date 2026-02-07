# PRD 06 — Viral Growth Flywheel: Gap Analysis

**Date:** 2026-02-06

## Acceptance Criteria Status

| # | Criterion | Status | Blocker |
|---|-----------|--------|---------|
| 1 | Seller posts buying need after quote | ⚠️ Partial | Backend prompt exists, no frontend CTA |
| 2 | Referral attribution on signup | ❌ Not wired | `auth.py` creates User without referral fields |
| 3 | K-factor measurable | ❌ No endpoint | Attribution data exists but no analytics |
| 4 | Collaborator→buyer onboarding | ❌ No funnel | Share links work but funnel not tracked |

## Root Cause

The **data models** are ready (User.referral_share_token, ShareLink.signup_conversion_count, etc.)
but the **wiring** is missing:

1. `auth.py:499` creates new User without setting `referral_share_token` or `signup_source`
2. No way to pass referral token from frontend → auth verify → user creation
3. No admin endpoint to query the referral graph or compute K-factor
4. ShareLink click tracking works but doesn't connect to the signup funnel

## Implementation Plan

### Task 1: Auth Referral Capture (AC #2, #4)
- Add `referral_token` optional field to `AuthVerifyRequest`
- In `auth_verify()`, when creating new user, set `referral_share_token` and `signup_source`
- Increment `ShareLink.signup_conversion_count` on referral signup
- Fire notification to the referrer: "Someone you shared with just joined!"

### Task 2: K-Factor + Referral Graph Endpoint (AC #3)
- `GET /admin/growth` — returns:
  - K-factor = avg(shares_per_user) × avg(signup_conversion_rate)
  - Referral graph: [{referrer_id, referrer_email, invited_count, invited_who_bought_count}]
  - Seller-to-buyer conversion rate
  - Collaborator-to-buyer funnel: share_clicks → signups → created_rows

### Task 3: Frontend Referral Token Passthrough (AC #2, #4)
- Share page captures referral token from URL
- Passes it through to auth verify call
- Frontend proxy route

### Task 4: Seller-to-Buyer Prompt Frontend (AC #1)
- Already have backend `buyer_prompt` in quote response
- Need frontend to render the CTA after seller submits quote

## Dependencies (all satisfied)
- Notification system: ✅ built (PRD 04)
- Seller quote flow: ✅ built
- ShareLink model: ✅ built
- User referral fields: ✅ built
