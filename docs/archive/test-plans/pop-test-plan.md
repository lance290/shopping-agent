# Pop (popsavings.com) — User Test Plan

**URL:** https://frontend-production-1306.up.railway.app/pop-site  
**Auth bypass (dev):** use code `000000` with any phone number  
**Guest mode:** works without login — list saved to browser localStorage

---

## Scenario 1 — Landing page first impression

**Goal:** Confirm the homepage loads and the CTAs work.

1. Open `/pop-site`. Expect: green-themed landing page with Pop avatar, hero headline, feature cards, "How Pop works" steps.
2. Click **Try Pop Now — It's Free**. Expect: navigates to `/pop-site/chat`.
3. Go back. Click **See How It Works**. Expect: smooth scroll to the how-it-works section.
4. Enter a phone number in the "Get Pop on your phone" form and submit. Expect: redirects to `/login?phone=...&brand=pop`.

**Potential issues to watch:**
- Pop avatar image (`/pop-avatar.png`) returns 404
- "Chat with Pop" nav link broken

---

## Scenario 2 — Guest: add grocery items via chat

**Goal:** Confirm the core chat → list flow works without an account.

1. Open `/pop-site/chat`. Expect: welcome message from Pop.
2. Type: **"I need milk, eggs, and bread"**
3. Expect: Pop replies confirming the items, and a list sidebar appears on the right with those 3 items.
4. Type: **"Also get some butter and orange juice"**
5. Expect: 2 more items added to the sidebar list. Total shows **5 items on list →** in the nav.

**Potential issues to watch:**
- Backend `/api/pop/chat` returns an error → Pop replies with "Oops, something went wrong"
- Items don't appear in the sidebar (check `data.list_items` in API response)
- Items appear duplicated on second message

---

## Scenario 3 — Guest: edit and delete items

**Goal:** Confirm list management works for guests.

1. After adding at least 2 items (Scenario 2), hover over an item in the sidebar. Expect: a red ✕ appears.
2. Click the item name. Expect: it becomes an inline editable input.
3. Change the text (e.g., "whole milk" → "2% milk") and press Enter. Expect: item updates in place.
4. Hover over another item and click ✕. Expect: item removed from list immediately.
5. Refresh the page. Expect: remaining edited items are still there (localStorage persisted).

**Potential issues to watch:**
- Edit doesn't commit on blur (double-commit guard bug)
- Items disappear on refresh (localStorage not saving)

---

## Scenario 4 — Guest: natural language variations

**Goal:** Confirm Pop understands different ways of expressing grocery needs.

Try each of the following messages separately and confirm Pop adds the right item(s):

| Input | Expected item(s) added |
|---|---|
| `"we're out of dish soap"` | Dish soap |
| `"get some snacks for the kids"` | Snacks (or similar) |
| `"yogurt, apples, and cheddar cheese"` | 3 items |
| `"I love pasta"` | **Nothing** — this is a statement, not a shopping request |

**Potential issues to watch:**
- "I love pasta" gets added as an item (NLU false positive)
- Multi-item comma lists only add the first item

---

## Scenario 5 — View full list page

**Goal:** Confirm the list detail page loads and shows deals/swaps.

1. Add several items via chat (Scenario 2 items work).
2. Once `projectId` is set (list has items), click **View Full List →** in the sidebar or the `N items on list →` nav badge.
3. Expect: navigates to `/pop-site/list/[id]`. Page shows each item as a card.
4. Expand an item. Expect: tabs for **Deals** and **Swaps** appear. Deals or swaps should be visible if the backend found any.
5. Click the checkbox next to an item. Expect: item gets a checked/strikethrough state.

**Potential issues to watch:**
- List page shows "Loading…" forever (check `/api/pop/list/[id]` in network)
- Deals tab is empty for all items (sourcing may not be wired up yet)
- Share / invite button on the list page fails

---

## Scenario 6 — Sign up with phone OTP

**Goal:** Confirm the phone auth flow works and list is preserved.

1. Add a few items to the guest list first (Scenario 2).
2. Click **Sign In** in the Pop chat nav.
3. On the login page, enter your phone number. Expect: "Code sent" step.
4. Enter `000000` (dev bypass). Expect: logged in, redirected back to `/pop-site/chat`.
5. Expect: the previously added guest items are still visible — logged-in mode loaded from DB.

**Potential issues to watch:**
- OTP page shows BuyAnything branding instead of Pop branding (check `brand=pop` param)
- Guest items lost after login (guest-to-user row claim not firing)
- Redirect after login goes to `/` instead of Pop chat

---

## Scenario 7 — Family invite link

**Goal:** Confirm the invite flow is accessible.

1. With a logged-in session and at least one list item, navigate to `/pop-site/list/[id]`.
2. Look for a **Share / Invite** button. Click it.
3. Expect: an invite link is generated (or copied to clipboard).
4. Open the invite link in a new incognito tab. Expect: `/pop-site/invite/[code]` loads and prompts to join the family list.

**Potential issues to watch:**
- Share button missing (may not be wired on the list page yet)
- Invite link 404s

---

## Scenario 8 — Wallet page

**Goal:** Confirm the wallet page renders (even if balance is $0).

1. Log in (Scenario 6).
2. Navigate to `/pop-site/wallet`.
3. Expect: page loads showing a wallet balance (likely $0.00) and a transaction history section (likely empty).

**Potential issues to watch:**
- Page crashes or returns 404
- Infinite loading spinner on wallet balance fetch
