# Smoke Test Checklist — Demo Day

**Production URL**: https://buy-anything.com  
**Time to complete**: ~5 minutes  
**Last verified**: Feb 17, 2026

---

## 1. Homepage / Workspace Loads
- [ ] Open https://buy-anything.com — chat panel + board visible, no white screen
- [ ] Empty board shows trending search pills and vendor pills

## 2. Public Pages (no login required)
- [ ] `/search` — search page loads
- [ ] `/vendors` — vendor directory loads, shows vendor cards
- [ ] `/guides` — guides index loads
- [ ] `/about`, `/privacy`, `/terms` — static pages render

## 3. Search (use your own queries)
- [ ] Type a search in chat → results stream in within a few seconds
- [ ] Offer cards appear with prices, images, source badges
- [ ] Click an offer card → opens product link in new tab
- [ ] Try a second search → new row appears, results populate

## 4. Login Flow (Real OTP)
- [ ] Go to `/login` → phone input appears
- [ ] Enter your real phone number → SMS arrives with 6-digit code
- [ ] Enter the OTP code → redirects to workspace
- [ ] Chat header shows your phone number

## 5. Social Features (Before Login)
- [ ] Click heart icon on an offer → toast prompts signup
- [ ] Click share icon → link copied + toast prompts signup

## 6. Social Features (After Login)
- [ ] Click heart icon → "Liked this offer" toast (heart fills)
- [ ] Click share icon → "Share link copied!" toast
- [ ] Click comment icon → prompt appears, submit → "Comment saved" toast

## 7. No Errors
- [ ] No white screens or crash pages at any point
- [ ] No "500" or "Something went wrong" messages

---

**Pass criteria**: All boxes checked, searches return results, OTP works, no crashes.
