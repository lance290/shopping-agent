# Task 02: Clickout + Tracking

**Priority:** P0  
**Estimated Time:** 2 days  
**Dependencies:** Task 01 (frontend wired to `/api/out`)  
**Outcome:** Every outbound click is logged, redirect works

---

## Objective

Implement the first-party clickout system so that:
1. No product link goes directly to merchant
2. Every click is logged with context (user, row, offer, source)
3. User is redirected to the correct merchant URL

---

## Why This Matters (Audit Note)

This is the **foundation of monetization**. Without this:
- We cannot track which clicks lead to revenue
- We cannot attribute affiliate commissions
- We cannot audit user behavior for compliance

---

## Implementation Steps

### Step 2.1: Add ClickoutEvent Model

**File:** `apps/backend/models.py`

```python
class ClickoutEvent(SQLModel, table=True):
    """Logs every outbound click for affiliate tracking and auditing."""
    __tablename__ = "clickout_event"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who clicked
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None)  # For anonymous tracking
    
    # What they clicked
    row_id: Optional[int] = Field(default=None, index=True)
    offer_index: int = 0  # Position in results (for ranking analysis)
    
    # URL info
    canonical_url: str  # Original URL from provider
    final_url: str  # URL after affiliate transformation (may be same)
    merchant_domain: str = Field(index=True)  # e.g., "amazon.com"
    
    # Affiliate info
    handler_name: str = "none"  # Which handler processed this
    affiliate_tag: Optional[str] = None  # e.g., "buyanything-20"
    
    # Provenance
    source: str = "unknown"  # e.g., "serpapi_google_shopping"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Future: conversion tracking
    # conversion_reported_at: Optional[datetime] = None
    # revenue_cents: Optional[int] = None
```

- [ ] Add model to `models.py`
- [ ] Ensure import of `datetime` if not present

**Test:** Model imports without error

---

### Step 2.2: Create Alembic Migration

**Command:**
```bash
cd apps/backend
alembic revision --autogenerate -m "add_clickout_event_table"
alembic upgrade head
```

- [ ] Generate migration
- [ ] Review migration file for correctness
- [ ] Apply to local database
- [ ] Test rollback: `alembic downgrade -1`

**Test:** Table exists in database, can insert/query

---

### Step 2.3: Add extract_merchant_domain Utility

**File:** `apps/backend/sourcing.py`

```python
from urllib.parse import urlparse

def extract_merchant_domain(url: str) -> str:
    """Extract the merchant domain from a URL.
    
    Examples:
        https://www.amazon.com/dp/B08N5... -> amazon.com
        https://shop.example.co.uk/product -> example.co.uk
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"
```

- [ ] Add function to `sourcing.py`
- [ ] Handle edge cases (empty URL, malformed URL)

**Test:** Unit test with various URL formats

---

### Step 2.4: Add merchant_domain to SearchResult

**File:** `apps/backend/sourcing.py`

```python
class SearchResult(BaseModel):
    title: str
    price: float
    currency: str = "USD"
    merchant: str
    url: str
    merchant_domain: str = ""  # NEW FIELD
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    shipping_info: Optional[str] = None
    source: str = "unknown"
```

Update each provider's `search()` method to populate `merchant_domain`:

```python
results.append(SearchResult(
    # ... existing fields ...
    url=url,
    merchant_domain=extract_merchant_domain(url),  # ADD THIS
))
```

- [ ] Add `merchant_domain` field to `SearchResult`
- [ ] Update `SerpAPIProvider.search()` 
- [ ] Update `SearchAPIProvider.search()`
- [ ] Update `RainforestAPIProvider.search()`
- [ ] Update `ValueSerpProvider.search()`
- [ ] Update `GoogleCustomSearchProvider.search()`
- [ ] Update `MockShoppingProvider.search()`

**Test:** Search results include `merchant_domain`

---

### Step 2.5: Implement /api/out Endpoint

**File:** `apps/backend/main.py`

```python
from fastapi.responses import RedirectResponse
from models import ClickoutEvent

class ClickoutRequest(BaseModel):
    url: str
    row_id: Optional[int] = None
    offer_index: int = 0
    source: str = "unknown"

@app.get("/api/out")
async def clickout_redirect(
    url: str,
    row_id: Optional[int] = None,
    idx: int = 0,
    source: str = "unknown",
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Log a clickout event and redirect to the merchant.
    
    Query params:
        url: The canonical merchant URL
        row_id: The procurement row this offer belongs to
        idx: The offer's position in search results
        source: The sourcing provider (e.g., serpapi_google_shopping)
    """
    # Validate URL
    if not url or not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    # Extract user if authenticated
    user_id = None
    session_id = None
    if authorization:
        auth_session = await get_current_session(authorization, session)
        if auth_session:
            user_id = auth_session.user_id
            session_id = auth_session.id
    
    # Extract merchant domain
    merchant_domain = extract_merchant_domain(url)
    
    # For now, final_url = canonical_url (Task 03 will add affiliate transformation)
    final_url = url
    handler_name = "none"
    
    # Log the clickout event
    event = ClickoutEvent(
        user_id=user_id,
        session_id=session_id,
        row_id=row_id,
        offer_index=idx,
        canonical_url=url,
        final_url=final_url,
        merchant_domain=merchant_domain,
        handler_name=handler_name,
        source=source,
    )
    session.add(event)
    await session.commit()
    
    # Redirect to merchant
    return RedirectResponse(url=final_url, status_code=302)
```

- [ ] Add endpoint to `main.py`
- [ ] Import `RedirectResponse` from `fastapi.responses`
- [ ] Import `extract_merchant_domain` from `sourcing`
- [ ] Handle missing/invalid URL gracefully

**Test:** 
- `GET /api/out?url=https://amazon.com/dp/123` → 302 redirect
- ClickoutEvent row created in database

---

### Step 2.6: Proxy /api/out in BFF

**File:** `apps/bff/src/index.ts`

```typescript
// Proxy clickout to backend (preserves auth header for user tracking)
fastify.get('/api/out', async (request, reply) => {
  try {
    const query = request.query as Record<string, string>;
    const params = new URLSearchParams(query).toString();
    
    const headers: Record<string, string> = {};
    if (request.headers.authorization) {
      headers['Authorization'] = request.headers.authorization;
    }
    
    const response = await fetch(`${BACKEND_URL}/api/out?${params}`, {
      headers,
      redirect: 'manual', // Don't follow redirect, pass it through
    });
    
    // Pass through the redirect
    const location = response.headers.get('location');
    if (location) {
      reply.redirect(302, location);
    } else {
      reply.status(response.status).send(await response.text());
    }
  } catch (err) {
    fastify.log.error(err);
    reply.status(500).send({ error: 'Clickout failed' });
  }
});
```

- [ ] Add route to BFF
- [ ] Pass through auth header
- [ ] Handle redirect properly

**Test:** Frontend `/api/out` call reaches backend, redirects work

---

### Step 2.7: Wire Frontend OfferTile (if not done in Task 01)

**File:** `apps/frontend/app/components/OfferTile.tsx`

Ensure the href uses the clickout URL format:

```tsx
const clickUrl = `/api/out?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`;
```

- [ ] Verify OfferTile uses correct URL format
- [ ] Test that clicks go to `/api/out`

**Test:** Click offer → redirect to merchant via `/api/out`

---

### Step 2.8: Add Admin Endpoint to View Clickouts

**File:** `apps/backend/main.py`

```python
@app.get("/admin/clickouts", response_model=List[ClickoutEvent])
async def list_clickouts(
    limit: int = 100,
    merchant_domain: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """List recent clickout events (admin only)."""
    # TODO: Add proper admin auth check
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    query = select(ClickoutEvent).order_by(ClickoutEvent.created_at.desc()).limit(limit)
    if merchant_domain:
        query = query.where(ClickoutEvent.merchant_domain == merchant_domain)
    
    result = await session.exec(query)
    return result.all()
```

- [ ] Add admin endpoint
- [ ] Filter by merchant_domain
- [ ] TODO: Implement proper admin role check (Task 06)

**Test:** Authenticated user can view clickout log

---

## Acceptance Criteria

- [ ] `ClickoutEvent` table exists with all required columns
- [ ] Every offer click goes through `/api/out`
- [ ] Clickout events are logged with: user_id, row_id, offer_index, canonical_url, merchant_domain, source
- [ ] User is redirected to correct merchant URL
- [ ] `/admin/clickouts` returns recent events

---

## Audit Considerations

- **Data Retention:** Clickout events should be retained for at least 90 days for affiliate reconciliation
- **PII:** `user_id` links to user email; consider anonymization policy
- **Tampering:** Events are insert-only; no update/delete endpoint exposed
- **Logging:** All clickouts are logged server-side (not client-side) for reliability

---

## Rollback Plan

1. Remove `/api/out` endpoint
2. Revert OfferTile to direct links
3. `alembic downgrade -1` to remove table (data loss!)

---

## Files Changed

| File | Action |
|------|--------|
| `apps/backend/models.py` | Add `ClickoutEvent` |
| `apps/backend/main.py` | Add `/api/out`, `/admin/clickouts` |
| `apps/backend/sourcing.py` | Add `extract_merchant_domain`, update `SearchResult` |
| `apps/bff/src/index.ts` | Add `/api/out` proxy |
| `apps/frontend/app/components/OfferTile.tsx` | Verify clickout URL |
| `alembic/versions/` | New migration |
