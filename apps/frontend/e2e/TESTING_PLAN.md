# BuyAnything.ai Comprehensive E2E Testing Plan

**Created:** 2026-01-25  
**Status:** Implementation Ready  
**Coverage Target:** 100% of Human User Interactions

---

## Executive Summary

This testing plan covers **every interaction a human user would perform** on the BuyAnything.ai platform, derived from:
1. `need sourcing_ next ebay.md` - Vision document
2. `agent-facilitated-competitive-bidding-prd.md` - Detailed PRD
3. `buyanything-ai-ai-agent-facilitated-multi-category-marketplace-PRD.md` - Full marketplace spec
4. Codebase analysis of all endpoints and UI components

---

## Feature Matrix: PRD → Implementation → Tests

| PRD Feature | Implemented | Backend Endpoint | Frontend Component | Test Coverage |
|-------------|-------------|------------------|-------------------|---------------|
| **Chat-based row creation** | ✅ | POST /rows | Chat.tsx | Suite 1, 2, 3 |
| **Project hierarchy** | ✅ | POST/GET/DELETE /projects | Board.tsx | Suite 1, 3 |
| **Row refinement** | ✅ | PATCH /rows/:id | Chat.tsx | Suite 1, 2 |
| **Search/sourcing** | ✅ | POST /rows/:id/search | RowStrip.tsx | Suite 1, 2 |
| **Bid/Offer display** | ✅ | GET /rows (with bids) | OfferTile.tsx | Suite 1, 2, 3 |
| **Offer selection** | ✅ | POST /rows/:id/options/:id/select | OfferTile.tsx | Suite 1, 2 |
| **Choice factors (RFP)** | ✅ | PATCH /rows/:id | ChoiceFactorPanel.tsx | Suite 1, 2 |
| **Clickout/affiliate** | ✅ | GET /api/clickout | OfferTile.tsx | Suite 1, 2 |
| **Bug reporting** | ✅ | POST /api/bugs | ReportBugModal.tsx | Suite 2 |
| **Authentication** | ✅ | POST /auth/* | OTP/Session | Suite 1, 3 |
| **User data isolation** | ✅ | All endpoints | All | Suite 3 |
| **Audit trail** | ✅ | GET /admin/audit | Admin | Suite 2 |

---

## Test Suite Architecture

### Suite 1: Happy Path User Journey
**Philosophy:** Simulate a complete, successful user experience from login to purchase selection.

**Scenarios:**
1. **First-time buyer journey**
   - Login/register
   - Create first search via chat
   - View offers
   - Refine search with constraints
   - Select winning offer
   - Verify clickout works

2. **Project-based procurement**
   - Create a project ("Office Setup")
   - Add multiple rows under project
   - Search for each row
   - Compare offers across rows
   - Select winners for each

3. **Choice factor interaction**
   - Start search
   - Answer choice factor questions
   - Verify search updates with answers
   - Change answers, verify re-search

### Suite 2: Edge Cases & Error Handling
**Philosophy:** Test error recovery, boundary conditions, and defensive behavior.

**Scenarios:**
1. **Empty/invalid inputs**
   - Empty search query
   - Very long search query (1000+ chars)
   - Special characters in search
   - SQL injection attempts
   - XSS attempts

2. **Network/API failures**
   - Search timeout handling
   - Auth token expiration
   - Backend unavailable

3. **Data boundary conditions**
   - Row with 0 bids
   - Row with 100+ bids
   - Project with 0 rows
   - Project with 50+ rows

4. **Concurrent operations**
   - Rapid multiple searches
   - Delete while search in progress
   - Update while viewing

### Suite 3: Multi-User & Data Isolation
**Philosophy:** Ensure complete data separation between users and proper access control.

**Scenarios:**
1. **User isolation**
   - User A creates rows
   - User B cannot see User A's rows
   - User B cannot access User A's row by ID

2. **Project isolation**
   - User A creates project
   - User B cannot see or modify

3. **Session management**
   - Logout invalidates session
   - Cannot access protected routes without auth
   - Token expiration handling

4. **Admin vs regular user**
   - Regular user cannot access /admin/*
   - Admin can access audit logs

---

## Detailed Test Cases

### 1. Authentication & Session Management

```
TC-AUTH-001: Email login flow
  Given: User is not logged in
  When: User enters email, receives code, enters code
  Then: User is authenticated and redirected to main app

TC-AUTH-002: Session persistence
  Given: User is logged in
  When: User refreshes page
  Then: User remains logged in

TC-AUTH-003: Logout
  Given: User is logged in
  When: User clicks logout
  Then: Session is invalidated, user redirected to login

TC-AUTH-004: Invalid token rejection
  Given: User has invalid/expired token
  When: User tries to access protected route
  Then: 401 error, redirect to login
```

### 2. Chat & Row Creation

```
TC-CHAT-001: Create row via chat
  Given: User is logged in, no active rows
  When: User types "I need a Montana State shirt XL blue"
  Then: New row created with title matching query
        Row appears in Board
        Search results appear

TC-CHAT-002: Refine existing row
  Given: User has active row "Montana State shirt"
  When: User types "make it under $50"
  Then: Same row updated (no new row)
        Search re-runs with constraint
        Results filtered by price

TC-CHAT-003: Create new unrelated row
  Given: User has active row "Montana State shirt"
  When: User types "I also need running shoes"
  Then: New row created for "running shoes"
        Original row unchanged
        Two rows visible in Board

TC-CHAT-004: Chat context awareness
  Given: User clicks on Row A, then Row B
  When: User types refinement
  Then: Refinement applies to Row B (active row)
```

### 3. Project Management

```
TC-PROJ-001: Create project
  Given: User is logged in
  When: User clicks "New Project", enters "Summer Trip"
  Then: Project appears in Board
        Project is empty (0 rows)

TC-PROJ-002: Add row to project
  Given: User has project "Summer Trip"
  When: User clicks "Add Request" inside project, searches "flights to Tokyo"
  Then: New row created under "Summer Trip" project
        Row shows project_id association

TC-PROJ-003: Delete project
  Given: User has project with 2 rows
  When: User deletes project
  Then: Project removed
        Rows still exist but ungrouped (project_id = null)

TC-PROJ-004: Project isolation
  Given: User A has project "My Project"
  When: User B requests GET /projects
  Then: User B does not see "My Project"
```

### 4. Search & Offers

```
TC-SEARCH-001: Basic search
  Given: User has row "laptop"
  When: Search executes
  Then: Multiple offers appear as tiles
        Each offer has: title, price, merchant, image

TC-SEARCH-002: Search with choice factor answers
  Given: User has row with choice_answers {"max_price": 500}
  When: Search executes
  Then: Results filtered/ranked by constraint

TC-SEARCH-003: Offer tile interaction
  Given: Search results displayed
  When: User hovers/clicks offer tile
  Then: Expanded details visible
        "Select" and "Open" actions available

TC-SEARCH-004: Empty results handling
  Given: User searches for "xyznonexistent12345"
  When: Search completes
  Then: "No results found" message displayed
        User can refine or try again
```

### 5. Offer Selection & Clickout

```
TC-SELECT-001: Select winning bid
  Given: Row has 5 offers
  When: User clicks "Select" on offer #3
  Then: Offer #3 marked as selected
        Row status changes to "closed"
        Other offers show as not-selected

TC-CLICK-001: Clickout tracking
  Given: User views offer with URL
  When: User clicks to open merchant page
  Then: Click logged to clickout_event table
        User redirected to merchant (via affiliate if applicable)

TC-CLICK-002: Affiliate link transformation
  Given: Offer URL is amazon.com product
  When: User clicks out
  Then: URL transformed with affiliate tag
        Redirect works correctly
```

### 6. Choice Factors (RFP Builder)

```
TC-FACTOR-001: Factor generation
  Given: User creates row "gaming laptop"
  When: Row is created
  Then: Relevant factors generated (budget, screen size, GPU)
        Factors appear in ChoiceFactorPanel

TC-FACTOR-002: Answer factor
  Given: Row has factor "max_budget" type=number
  When: User enters "1500"
  Then: Answer saved to choice_answers
        Search can re-run with this constraint

TC-FACTOR-003: Regenerate factors
  Given: Row has generic factors
  When: User clicks "Regenerate Options"
  Then: LLM generates new category-specific factors
        UI updates with new questions
```

### 7. Bug Reporting

```
TC-BUG-001: Submit bug report
  Given: User encounters issue
  When: User opens bug modal, fills form, attaches screenshot
  Then: Bug saved to database
        GitHub issue created (if configured)
        User sees confirmation

TC-BUG-002: Bug with diagnostics
  Given: Bug modal open
  When: User submits with diagnostics enabled
  Then: Console logs, network info captured
        Sensitive data redacted
```

### 8. Data Isolation & Security

```
TC-SEC-001: Row access control
  Given: User A owns row #123
  When: User B requests GET /rows/123
  Then: 404 Not Found (not 403, to prevent enumeration)

TC-SEC-002: Project access control
  Given: User A owns project #456
  When: User B requests DELETE /projects/456
  Then: 404 Not Found

TC-SEC-003: Rate limiting
  Given: User makes 31 searches in 60 seconds
  When: 31st search requested
  Then: 429 Too Many Requests

TC-SEC-004: Input sanitization
  Given: User enters "<script>alert(1)</script>" in chat
  When: Displayed in UI
  Then: HTML escaped, no script execution
```

---

## Test Data Fixtures

### Users
```typescript
const TEST_USERS = {
  buyer1: { email: 'buyer1@test.com' },
  buyer2: { email: 'buyer2@test.com' },
  seller1: { email: 'seller1@test.com' },
  admin: { email: 'admin@test.com', is_admin: true },
};
```

### Sample Searches
```typescript
const SAMPLE_QUERIES = [
  'Montana State long sleeve shirt XL blue',
  'gaming laptop under $1500',
  'office chair ergonomic mesh',
  'wireless headphones noise cancelling',
  'running shoes size 10 men',
];
```

### Sample Projects
```typescript
const SAMPLE_PROJECTS = [
  { title: 'Office Setup', rows: ['desk', 'chair', 'monitor', 'keyboard'] },
  { title: 'Summer Trip', rows: ['flights', 'hotel', 'car rental'] },
  { title: 'Home Renovation', rows: ['paint', 'flooring', 'light fixtures'] },
];
```

---

## Execution Strategy

### Prerequisites
1. Backend running on port 8000 with `E2E_TEST_MODE=1`
2. BFF running on port 8080
3. Frontend running on port 3000
4. Database seeded or clean state

### Run Commands
```bash
# All tests
pnpm exec playwright test

# Specific suite
pnpm exec playwright test e2e/suite1-happy-path.spec.ts
pnpm exec playwright test e2e/suite2-edge-cases.spec.ts
pnpm exec playwright test e2e/suite3-multi-user.spec.ts

# With UI (headed mode)
pnpm exec playwright test --headed

# Debug mode
pnpm exec playwright test --debug
```

---

## Success Criteria

- [ ] All 3 test suites pass consistently
- [ ] No flaky tests (3 consecutive runs pass)
- [ ] Coverage of 100% of PRD user stories
- [ ] Average test run time < 5 minutes
- [ ] Clear failure messages for debugging
