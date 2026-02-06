# Code Review Issues - Iteration 4 (Pass 2 fixes verified)

## Summary
All 4 issues from Iteration 3 have been resolved. No new issues introduced.

### Fixes Applied
| ID | Severity | Fix |
|----|----------|-----|
| M5 | Major | Added authz check: `handoff.buyer_user_id != auth_session.user_id` → 403 |
| M6 | Major | Added auth to `send_reminders` endpoint (imported Header + get_current_session) |
| m4 | Minor | Changed `catch (err: any)` → `catch (err: unknown)` in quote page (2 locations) |
| m5 | Minor | Fixed misleading success toast in handleShare — now shows error on failure |

### Cumulative Fix Summary (Pass 1 + Pass 2)
| ID | Severity | Issue | Status |
|----|----------|-------|--------|
| C1 | Critical | `backend_url` undefined in send_outreach_email | ✅ Fixed |
| C2 | Critical | Merchant register direct BFF call | ✅ Fixed |
| M1 | Major | close_handoff no authn | ✅ Fixed |
| M2 | Major | Merchant search leaks email | ✅ Fixed |
| M3 | Major | DRY: normalizeBaseUrl duplicated | ✅ Fixed |
| M4 | Major | Merchant search scaling TODO | ✅ Fixed |
| M5 | Major | close_handoff no authz | ✅ Fixed |
| M6 | Major | send_reminders no auth | ✅ Fixed |
| m4 | Minor | err:any in quote page | ✅ Fixed |
| m5 | Minor | Misleading share toast | ✅ Fixed |

### Accepted Minor/Nits (not fixed)
- m1: `import json` inside function body in outreach.py (pre-existing pattern)
- m2: GET `/unsubscribe` modifies state (acceptable for email link UX)
- m3: ContractResponse construction duplicated (only 2 occurrences)
- n1: `print()` vs `logging` in contracts.py (demo mode only)
- Pre-existing lint warnings in RowStrip.tsx (out of scope)

### Tests
- 271 passed, 18 warnings, 0 failures

## Verdict: PASS ✅
