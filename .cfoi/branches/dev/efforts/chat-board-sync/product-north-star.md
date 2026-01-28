# Effort North Star (Effort: Chat-Board Sync, v2026-01-08)

## Goal Statement
Establish robust bidirectional synchronization between the Chat interface and the Procurement Board, with Zustand as the single source of truth, ensuring all user interactions flow correctly and persist to the database.

## Ties to Product North Star

| Product North Star Element | How This Effort Supports It |
|---------------------------|----------------------------|
| "Chat-native procurement" | Chat input creates/updates board cards seamlessly |
| "Zustand as source of truth" | All state flows through centralized store |
| "Time to first request <15s" | Instant card creation from chat message |
| "Transparency / Audit trail" | All state changes are traceable through store |

## In Scope

1. **Step 1 (User types search)**:
   - 1a. User types in chat
   - 1b. Search query saved to Zustand
   - 1c. Card selected or created
   - 1d. Database updated with query
   - 1e. Search executed
   - 1f. Results saved to Zustand and DB

2. **Step 2 (User extends search)**:
   - Detect if new search or extension of existing
   - Reuse active card for extensions (no duplicates)
   - Update Zustand and DB accordingly

3. **Step 3 (User clicks card)**:
   - Set query in Zustand
   - Append card text to chat
   - Run search
   - Continue to Step 2 flow

## Out of Scope

- Seller bidding workflow
- Payment/checkout flow
- Multi-user collaboration
- Offline support

## Acceptance Checkpoints

| Checkpoint | Verification Method | Status |
|------------|---------------------|--------|
| Card created on first search | Playwright E2E test | ✅ Passing |
| No duplicate card on search extension | Playwright E2E test | ✅ Passing |
| Card click appends text to chat | Playwright E2E test | ✅ Passing |
| Zustand store logic correct | Vitest unit tests (4 tests) | ✅ Passing |
| Type validation (constraints) | Manual + deployed fix | ✅ Fixed |

## Dependencies & Risks

**Dependencies**:
- Zustand store (`apps/frontend/app/store.ts`)
- Chat component (`apps/frontend/app/components/Chat.tsx`)
- RequestsSidebar component (`apps/frontend/app/components/RequestsSidebar.tsx`)
- BFF LLM tools (`apps/bff/src/llm.ts`)

**Risks**:
- LLM may not always detect "extension" vs "new search" correctly
- Race conditions between optimistic updates and DB responses
- Selector drift if UI structure changes (mitigated by E2E tests)

## Approver / Date
- **Created**: 2026-01-08
- **Product North Star Version**: v2026-01-08
- **Status**: Complete - All checkpoints passing
