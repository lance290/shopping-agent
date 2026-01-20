# UI/UX Feedback for Investor Demo

These issues should be addressed to make the app screenshot-ready for investors.

---

## Issue 1: Add "+ New Request" Button

**Priority:** High (investor demo)

**Current behavior:** Users must type in the chat to create a new procurement request. There's no obvious visual affordance.

**Expected behavior:** A prominent "+ New Request" button should appear:
- At the top of the procurement board (always visible)
- Optionally at the bottom when scrolling

**Acceptance criteria:**
- [ ] Button is visually prominent (e.g., blue with plus icon)
- [ ] Clicking it focuses the chat input with placeholder "What are you looking for?"
- [ ] Works on mobile

---

## Issue 2: Add "View Deal" CTA Button on Offer Tiles

**Priority:** High (investor demo)

**Current behavior:** The entire offer tile is clickable, but there's no clear call-to-action button. Users may not realize they can click through.

**Expected behavior:** Add a visible "View Deal →" or "Shop Now" button at the bottom of each offer tile.

**Acceptance criteria:**
- [ ] Button is visually distinct (e.g., blue background, white text)
- [ ] Hover state provides feedback
- [ ] Clicking opens merchant link in new tab (same as current tile click)

---

## Issue 3: Add Option Selection (Mark as "Chosen")

**Priority:** Medium

**Current behavior:** Users can browse offers but can't mark one as their chosen option. No way to track which item they decided on.

**Expected behavior:** Each offer tile should have a "Select" or checkmark button. When clicked:
- The offer is visually highlighted as "selected"
- The row status updates to "selected" or "closed"
- Selection is persisted to the database

**Acceptance criteria:**
- [ ] "Select" button or checkbox on each offer tile
- [ ] Selected offer has distinct visual treatment (green border, checkmark badge)
- [ ] Only one offer per row can be selected
- [ ] Selection persists across page refresh

---

## Issue 4: Loading State Improvements

**Priority:** Medium

**Current behavior:** When searching, the offer area shows "Searching for offers..." text. Minimal visual feedback.

**Expected behavior:** Add skeleton loaders or animated placeholders while offers are loading to make the app feel more responsive.

**Acceptance criteria:**
- [ ] Skeleton cards appear during search
- [ ] Subtle animation (pulse or shimmer)
- [ ] Graceful transition when results arrive

---

## Issue 5: Empty Board State Enhancement

**Priority:** Low

**Current behavior:** Empty board shows an emoji and text prompt. Functional but basic.

**Expected behavior:** Make the empty state more visually engaging:
- Larger, more polished illustration or icon
- Example prompts the user can click to try
- Subtle animation to draw attention

**Acceptance criteria:**
- [ ] Professional-looking empty state graphic
- [ ] 2-3 clickable example queries (e.g., "Try: Blue running shoes under $100")
- [ ] Clicking example auto-fills chat and submits

---

## Issue 6: Mobile Responsive Layout

**Priority:** Low (unless demo on mobile)

**Current behavior:** Layout is desktop-optimized. May not work well on mobile/tablet.

**Expected behavior:** 
- Chat and board stack vertically on mobile
- Offer tiles are swipeable
- Touch-friendly tap targets

**Acceptance criteria:**
- [ ] Breakpoint at 768px switches to mobile layout
- [ ] All interactive elements are 44px+ tap targets
- [ ] Horizontal scroll works with touch

---

## Notes for Implementation

- Issues 1 and 2 are highest priority for investor screenshots
- Issue 3 completes the PRD's "select an option" flow
- Issues 4-6 are polish items

