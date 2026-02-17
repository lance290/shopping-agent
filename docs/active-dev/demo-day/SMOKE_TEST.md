# Smoke Test Checklist — Demo Day

**URL**: http://localhost:3003 (local) or production URL  
**Time to complete**: ~5 minutes  
**Last verified**: Feb 17, 2026

---

## 1. Homepage / Workspace Loads
- [ ] Open `/` — chat panel + board visible, no white screen
- [ ] Empty board shows trending search pills and vendor pills

## 2. Public Pages (no login required)
- [ ] `/search` — search page loads
- [ ] `/vendors` — vendor directory loads, shows vendor cards
- [ ] `/guides` — guides index loads
- [ ] `/about`, `/privacy`, `/terms` — static pages render

## 3. Search (Anonymous)
- [ ] Type "Roblox gift cards" in chat → results stream in
- [ ] Offer cards appear with prices, images, source badges
- [ ] Click an offer card → opens product link in new tab

## 4. Search (Service/Vendor Tier)
- [ ] Type "caterer for 50 person corporate event" → results appear
- [ ] Vendor directory results show alongside web results
- [ ] Results include vendor names and "Get Quote" or contact options

## 5. Social Features (Anonymous)
- [ ] Click heart icon on an offer → toast says "Sign up to save likes..."
- [ ] Click comment icon → prompt appears, submit → toast says "Create an account..."
- [ ] Click share icon → link copied + toast about signup

## 6. Login Flow
- [ ] Go to `/login` → phone input appears
- [ ] Enter any phone number → OTP screen appears
- [ ] Enter code `000000` (dev bypass) → redirects to workspace
- [ ] Chat header shows phone number or email

## 7. Social Features (Logged In)
- [ ] Click heart icon → "Liked this offer" toast
- [ ] Click share icon → "Share link copied!" toast

## 8. No Console Errors
- [ ] Open browser DevTools → Console tab
- [ ] No red errors on page load or during search

---

**Pass criteria**: All boxes checked, no white screens, no 500 errors.
