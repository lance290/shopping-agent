# BuyAnything — User Test Plan

**URL:** https://frontend-production-1306.up.railway.app  
**Auth bypass (dev):** use code `000000` with any phone number

---

## Scenario 1 — First-time visitor, anonymous search

**Goal:** Confirm the empty-state board and anonymous search work.

1. Open the app. Expect: empty board with "Type in the chat to search for anything" prompt, trending search cards, vendor pills.
2. Click one of the trending cards (e.g., **Robot lawn mowers**). Expect: card dismisses with animation, chat fires the query automatically, a new row appears on the board, offer tiles load.
3. Refresh the page. Expect: row is still there (persisted to DB even without login).

**Potential issues to watch:**
- Offer tiles show placeholder images or "$0.00" — should show actual prices or "Request Quote"
- Loading spinner never clears — streaming lock timeout bug

---

## Scenario 2 — Budget-constrained search

**Goal:** Verify constraints are captured and applied to results.

1. In the chat, type: **"Standing desks under $600"**
2. Expect: a row is created, results load, nothing priced over $600 appears.
3. Follow up in the same chat: **"Actually, keep it under $400"**
4. Expect: the same row updates (not a new one), results reprice accordingly.

**Potential issues to watch:**
- A second row created instead of updating the first
- Results over the price cap slip through

---

## Scenario 3 — Multi-topic board

**Goal:** Confirm separate searches create separate rows.

1. Search for **"espresso machines"**. Wait for results.
2. Without clicking anything, type **"air purifiers for wildfire smoke"** in the chat.
3. Expect: a second row appears. The active row highlights switch. Results for each topic stay with the correct row.
4. Click the first row's tile on the board. Expect: chat focus message changes to the espresso row.

**Potential issues to watch:**
- Results from search 2 appearing under row 1
- Active row highlight not switching

---

## Scenario 4 — Service / vendor request

**Goal:** Confirm vendor-directory results appear for service requests.

1. Click the **caterers** vendor pill on the empty board, or type **"I need a caterer for a 50-person event"** in chat.
2. Expect: vendor tiles appear instead of (or alongside) product tiles. Tiles show "Request Quote" button rather than a price.
3. Click **Request Quote** on a tile. Expect: an email compose or contact modal opens.

**Potential issues to watch:**
- "$0.00" shown instead of "Request Quote"
- Vendor tiles not appearing (vector search may need credits)

---

## Scenario 5 — Projects and grouping

**Goal:** Confirm requests can be organized under a project.

1. Click **New Project** in the board header. Give it a name (e.g., "Home Office").
2. Click the project name to arm it (blue highlight).
3. Type a new request: **"ergonomic office chair"**. Expect: the new row appears indented under "Home Office".
4. Type another request: **"USB-C monitor"**. Expect: second row also lands in the project.
5. Click **Add Request** next to the project name and type **"cable management kit"**. Expect: third row added.

**Potential issues to watch:**
- New row lands in "Other Requests" instead of the project
- Project arm state lost between requests

---

## Scenario 6 — Share board

**Goal:** Confirm the share link produces a readable read-only view.

1. Run at least one search so the board has rows.
2. Click **Share Board** in the header. Expect: a shareable URL is copied to clipboard (toast confirms).
3. Open the URL in an incognito window. Expect: results are visible without login, with affiliate disclosure shown.

**Potential issues to watch:**
- Share link generates a 404
- Offers missing on the share page

---

## Scenario 7 — Sign up and data continuity

**Goal:** Confirm anonymous rows are claimed after sign-in.

1. Run a search **without** logging in (e.g., "pellet grills").
2. Click **Account → Sign In** in the board header.
3. Enter a phone number and confirm with code `000000` (dev bypass).
4. After redirect back to the board, confirm the "pellet grills" row is still there and attributed to your account.

**Potential issues to watch:**
- Anonymous rows disappear after login
- Auth redirect loop

---

## Scenario 8 — Likes and offer interaction

**Goal:** Verify liking an offer persists.

1. Run a product search and wait for tiles.
2. Click the ❤️ like button on a tile. Expect: button changes state (pressed).
3. Refresh the page. Expect: liked state is preserved on the tile.
4. Click the 💬 comment button. Add a short note. Expect: comment count badge increments.

**Potential issues to watch:**
- Like silently fails (check network tab — should be `POST /likes`)
- Like state resets on refresh
