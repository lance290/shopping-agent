Task: Fix Search Row Persistence Bug
Problem
Rows created via LLM chat don't appear in the sidebar. The frontend doesn't refresh after the backend creates rows, and user isolation may be incomplete.

Tasks
1. Backend: Verify User Isolation on Row Endpoints
POST /rows - Ensure user_id is set from AuthSession.user_id (not from request body)
GET /rows - Ensure query filters by WHERE user_id = :current_user_id
GET /rows/{id} - Ensure ownership check before returning
DELETE /rows/{id} - Ensure ownership check before deleting
Verify RequestSpec is created with correct row_id linkage
2. BFF: Verify Auth Header Forwarding
createRow tool - Confirm Authorization header is forwarded to backend
/api/rows proxy - Confirm auth header passthrough
Verify tool returns { status: 'row_created', row_id, data } on success
3. Frontend: Fix Sidebar Refresh After Row Creation
Chat.tsx - After receiving row_created event, call fetchRows() to refresh from DB
RequestsSidebar.tsx - Subscribe to store.rows and re-render on change
RequestsSidebar.tsx - Fetch rows from DB on mount (useEffect)
Zustand store - Ensure setRows() action exists and triggers re-render
Auth - Verify sa_session cookie is sent with /api/rows requests
4. E2E Tests
Row persistence test - Create row via API, verify visible in UI, reload page, verify still visible
User isolation test - Two users create rows, each only sees their own
5. Verification
Row appears in sidebar immediately after LLM creates it
Row persists after page reload
Row persists after logout/login (same user)
Different users see only their own rows
No duplicate rows created
Debugging Reference
If rows don't appear:

Check browser console for [Chat] logs
Check network tab: /api/rows → status 200? response has rows?
Check backend logs for row creation
Query DB: SELECT * FROM row ORDER BY id DESC LIMIT 5;
Verify auth: sa_session cookie → BFF → Backend


# Search Tracking & Persistence Specification

## Problem Statement

The Shopping Agent app has a critical bug where:
1. **Rows created via LLM chat don't appear in the sidebar** - The LLM creates rows in the database, but the frontend sidebar doesn't refresh to show them
2. **Source of truth is fragmented** - State exists in Zustand (frontend), BFF, and Backend DB with no clear synchronization
3. **User isolation is unclear** - Rows must be scoped to the authenticated user

## Current Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  Next.js    │────▶│    BFF      │────▶│   Backend   │
│  (React)    │     │  API Routes │     │  (Fastify)  │     │  (FastAPI)  │
│             │     │             │     │             │     │             │
│  Zustand    │     │  Proxies    │     │  LLM Tools  │     │  PostgreSQL │
│  Store      │     │  + Auth     │     │  + Proxies  │     │  (SQLModel) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Current Flow (Broken)

1. User types "Montana State shirts" in chat
2. Frontend sends to `/api/chat` → BFF `/api/chat`
3. BFF calls LLM, LLM calls `createRow` tool
4. `createRow` tool POSTs to Backend `/rows` with auth header
5. Backend creates Row + RequestSpec in DB, returns row
6. BFF streams "✅ Adding..." to frontend
7. **BUG**: Frontend tries to refresh rows but timing/auth issues cause empty result
8. Sidebar shows "No requests yet"

## Required Behavior

### 1. Row Creation Flow

When a user creates a new search:

```
1. User submits query via chat
2. LLM decides to create a row → calls createRow tool
3. Backend creates Row with:
   - title: query text
   - status: "sourcing"
   - user_id: from auth session
   - request_spec: { item_name, constraints }
4. Backend returns created row with ID
5. BFF streams confirmation to frontend
6. Frontend MUST refresh sidebar to show new row
7. Row MUST persist across page reloads
```

### 2. Source of Truth

**PostgreSQL is the ONLY source of truth.**

- Zustand store is a **cache** that must sync with DB
- Every mutation (create/update/delete) goes to DB first
- After DB confirms, update Zustand
- On page load, fetch from DB to populate Zustand

### 3. User Isolation

All rows MUST be scoped to the authenticated user:

```sql
-- Backend query pattern
SELECT * FROM row WHERE user_id = :current_user_id
```

- `user_id` comes from `AuthSession.user_id`
- Session token is passed via `Authorization: Bearer <token>` header
- Frontend extracts token from `sa_session` cookie

## Implementation Requirements

### Frontend (Chat.tsx)

```typescript
// After LLM creates a row, IMMEDIATELY refresh from DB
const handleRowCreated = async () => {
  // Wait for backend commit
  await new Promise(r => setTimeout(r, 500));
  
  // Fetch fresh rows from DB
  const res = await fetch('/api/rows');
  if (res.ok) {
    const rows = await res.json();
    store.setRows(rows);
  }
};
```

### Frontend (RequestsSidebar.tsx)

```typescript
// Subscribe to store.rows changes - re-render automatically
const rows = useShoppingStore(state => state.rows);

// On mount, fetch from DB
useEffect(() => {
  fetchRows();
}, []);
```

### BFF (llm.ts - createRow tool)

```typescript
execute: async (input) => {
  const response = await fetch(`${BACKEND_URL}/rows`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authorization, // MUST forward auth
    },
    body: JSON.stringify({
      title: input.item,
      status: 'sourcing',
      request_spec: {
        item_name: input.item,
        constraints: JSON.stringify(input.constraints || {})
      }
    })
  });
  
  if (!response.ok) {
    return { status: 'error', error: await response.text() };
  }
  
  const row = await response.json();
  return { status: 'row_created', row_id: row.id, data: row };
}
```

### Backend (main.py - create_row)

```python
@app.post("/rows", response_model=Row)
async def create_row(row: RowCreate, ...):
    # 1. Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401)
    
    # 2. Create row with user_id
    db_row = Row(
        title=row.title,
        status=row.status,
        user_id=auth_session.user_id  # CRITICAL
    )
    session.add(db_row)
    await session.commit()
    await session.refresh(db_row)
    
    # 3. Create linked RequestSpec
    db_spec = RequestSpec(row_id=db_row.id, ...)
    session.add(db_spec)
    await session.commit()
    
    return db_row
```

### Backend (main.py - read_rows)

```python
@app.get("/rows", response_model=List[Row])
async def read_rows(...):
    # MUST filter by user_id
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401)
    
    result = await session.execute(
        select(Row).where(Row.user_id == auth_session.user_id)
    )
    return result.scalars().all()
```

## Testing Requirements

### E2E Test: Row Persistence

```typescript
test('row persists after creation and reload', async ({ page, request }) => {
  // 1. Create session
  const session = await mintSession(request);
  await setSessionCookie(page, session.token);
  
  // 2. Create row via API
  const row = await createRow(request, session.token, 'Test Item');
  expect(row.id).toBeDefined();
  expect(row.title).toBe('Test Item');
  
  // 3. Load page - row should appear
  await page.goto('/');
  await expect(page.locator(`text=Test Item`)).toBeVisible();
  
  // 4. Reload - row should still appear
  await page.reload();
  await expect(page.locator(`text=Test Item`)).toBeVisible();
});
```

### E2E Test: User Isolation

```typescript
test('users only see their own rows', async ({ request }) => {
  // Create two users
  const user1 = await mintSession(request, 'user1@test.com');
  const user2 = await mintSession(request, 'user2@test.com');
  
  // User 1 creates a row
  await createRow(request, user1.token, 'User 1 Item');
  
  // User 2 creates a row
  await createRow(request, user2.token, 'User 2 Item');
  
  // User 1 should only see their row
  const user1Rows = await getRows(request, user1.token);
  expect(user1Rows).toHaveLength(1);
  expect(user1Rows[0].title).toBe('User 1 Item');
  
  // User 2 should only see their row
  const user2Rows = await getRows(request, user2.token);
  expect(user2Rows).toHaveLength(1);
  expect(user2Rows[0].title).toBe('User 2 Item');
});
```

## Debugging Checklist

When rows don't appear:

1. **Check browser console** for `[Chat]` logs
2. **Check network tab** for `/api/rows` requests
   - Is status 200?
   - Is response an array with rows?
3. **Check backend logs** for row creation
4. **Check database** directly:
   ```sql
   SELECT * FROM row ORDER BY id DESC LIMIT 5;
   ```
5. **Verify auth flow**:
   - Is `sa_session` cookie present?
   - Is it being forwarded to BFF?
   - Is BFF forwarding to backend?

## Success Criteria

- [ ] Row appears in sidebar immediately after LLM creates it
- [ ] Row persists after page reload
- [ ] Row persists after logout/login
- [ ] Different users see only their own rows
- [ ] E2E tests pass for persistence and isolation
- [ ] No duplicate rows created


Keep repeating until source of truth is clear and synchronized, is persistent across sessions, is displayed properly in the UI, and is accessible to all components that need it, and all tests pass, and is isolated per user, and code is clean and maintainable.
