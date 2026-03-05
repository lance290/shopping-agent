# PRD: Phase 5 - Speed UX for High-Frequency List Entry

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
PopSavings needs to be faster than native notes apps for rapid grocery list entry. Currently, the UI auto-collapses sections and loses chat input focus after submitting an item, forcing the user to grab the mouse or tap the screen again. This PRD addresses these friction points to enable high-speed keyboard-only entry.

## 2. Goals & Acceptance Criteria
- **List Expanded by Default:** List sections (e.g., categories or departments) should render in an expanded state so newly added items are immediately visible.
- **No Auto-Collapse (Accordion Disabled):** Expanding one section must not contract other open sections.
- **Persistent Chat Focus:** After the user hits "Send" or presses Enter to submit a chat message, the focus must immediately return to the chat input field.
- **Acceptance Criteria:** A user can type an item, press Enter, and immediately type the next item without touching the mouse/screen. Doing this 5 times results in 5 visible items in the expanded list.

## 3. Scope
- **In-Scope:** Frontend React/TypeScript changes to the List component (accordion/expansion state) and Chat Input component (focus management).
- **Out-of-Scope:** Backend changes (no API or DB changes required for this specific speed UX).

## 4. Technical Implementation Notes
### Frontend (React)
1. **Accordion State Management:** 
   - Locate the component rendering the list sections (likely using a UI library like shadcn/ui or Radix). 
   - Change the `type="single" collapsible` prop to `type="multiple"` or equivalent so multiple sections can remain open.
   - Set the default value to an array of all section IDs/keys to ensure they are open on mount.
2. **Chat Input Focus:**
   - Locate the chat submission handler.
   - Use a React `useRef` attached to the input/textarea element.
   - On successful submission (or immediately after clearing the input state), invoke `inputRef.current?.focus()`.

## 5. Testing Requirements
- Unit/Component tests verifying the chat input retains focus after form submission.
- Integration tests ensuring multiple list sections can be open simultaneously.
- E2E tests simulating sequential multi-item keyboard entry.
