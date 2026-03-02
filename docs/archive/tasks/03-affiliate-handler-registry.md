# Task 03: Affiliate Handler Registry

**Priority:** P0  
**Estimated Time:** 2 days  
**Dependencies:** Task 02 (clickout infrastructure)  
**Outcome:** Pluggable affiliate URL transformation, first handlers live

---

## Objective

Create a handler registry system that:
1. Routes each clickout URL to the appropriate affiliate handler
2. Transforms URLs to include affiliate tags/codes
3. Supports adding new handlers without code changes to core clickout
4. Falls back gracefully when no handler matches

---

## Why This Matters (Audit Note)

This is where **revenue happens**. Each handler represents a monetization channel.
- Handlers must be auditable (which handler processed which click)
- Configuration must be versioned (for debugging revenue discrepancies)
- New handlers should ship weekly without touching core code

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LinkResolver                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 1. Match domain to handler                       │    │
│  │ 2. Call handler.transform(url, context)          │    │
│  │ 3. Return ResolvedLink (final_url, handler_name) │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│    ┌────────────┬───────┴───────┬────────────┐          │
│    ▼            ▼               ▼            ▼          │
│ Amazon      Ebay         Skimlinks    NoAffiliate       │
│ Handler     Handler      Handler      Handler           │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 3.1: Create affiliate.py Module

**New File:** `apps/backend/affiliate.py`

```python
"""
Affiliate Link Handler Registry

This module provides a pluggable system for transforming outbound URLs
to include affiliate tracking codes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, List
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import os


@dataclass
class ClickContext:
    """Context passed to handlers for URL transformation."""
    user_id: Optional[int]
    row_id: Optional[int]
    offer_index: int
    source: str
    merchant_domain: str


@dataclass
class ResolvedLink:
    """Result of affiliate link resolution."""
    final_url: str
    handler_name: str
    affiliate_tag: Optional[str] = None
    rewrite_applied: bool = False
    metadata: Optional[Dict] = None


class AffiliateHandler(ABC):
    """Base class for affiliate handlers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this handler."""
        pass
    
    @property
    @abstractmethod
    def domains(self) -> List[str]:
        """List of domains this handler can process."""
        pass
    
    @abstractmethod
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        """Transform the URL to include affiliate tracking."""
        pass


class NoAffiliateHandler(AffiliateHandler):
    """Default handler that passes URL through unchanged."""
    
    @property
    def name(self) -> str:
        return "none"
    
    @property
    def domains(self) -> List[str]:
        return []  # Matches nothing, used as fallback
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        return ResolvedLink(
            final_url=url,
            handler_name=self.name,
            rewrite_applied=False,
        )


class AmazonAssociatesHandler(AffiliateHandler):
    """Amazon Associates affiliate handler."""
    
    def __init__(self, tag: Optional[str] = None):
        self.tag = tag or os.getenv("AMAZON_AFFILIATE_TAG", "")
    
    @property
    def name(self) -> str:
        return "amazon_associates"
    
    @property
    def domains(self) -> List[str]:
        return [
            "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
            "amazon.it", "amazon.es", "amazon.ca", "amazon.com.au",
            "amazon.co.jp", "amazon.in", "amazon.com.mx", "amazon.com.br",
        ]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        if not self.tag:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No affiliate tag configured"},
            )
        
        # Parse URL and add/replace tag parameter
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params['tag'] = [self.tag]
        
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
        
        return ResolvedLink(
            final_url=new_url,
            handler_name=self.name,
            affiliate_tag=self.tag,
            rewrite_applied=True,
        )


class EbayPartnerHandler(AffiliateHandler):
    """eBay Partner Network handler (simplified rover link)."""
    
    def __init__(self, campaign_id: Optional[str] = None):
        self.campaign_id = campaign_id or os.getenv("EBAY_CAMPAIGN_ID", "")
    
    @property
    def name(self) -> str:
        return "ebay_partner"
    
    @property
    def domains(self) -> List[str]:
        return ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.fr", "ebay.it", "ebay.es"]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        if not self.campaign_id:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No campaign ID configured"},
            )
        
        # eBay uses rover redirect links
        # Simplified: append campaign to URL params (real impl uses rover.ebay.com)
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params['campid'] = [self.campaign_id]
        query_params['toolid'] = ['10001']  # Standard tool ID
        
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
        
        return ResolvedLink(
            final_url=new_url,
            handler_name=self.name,
            affiliate_tag=self.campaign_id,
            rewrite_applied=True,
        )


class LinkResolver:
    """
    Routes URLs to appropriate affiliate handlers.
    
    Usage:
        resolver = LinkResolver()
        result = resolver.resolve(url, context)
    """
    
    def __init__(self):
        self.handlers: Dict[str, AffiliateHandler] = {}
        self.domain_map: Dict[str, str] = {}  # domain -> handler_name
        self.default_handler = NoAffiliateHandler()
        
        # Register built-in handlers
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """Register handlers that are always available."""
        self.register(AmazonAssociatesHandler())
        self.register(EbayPartnerHandler())
    
    def register(self, handler: AffiliateHandler):
        """Register a handler and map its domains."""
        self.handlers[handler.name] = handler
        for domain in handler.domains:
            self.domain_map[domain] = handler.name
    
    def resolve(self, url: str, context: ClickContext) -> ResolvedLink:
        """
        Resolve a URL to its affiliate-transformed version.
        
        Args:
            url: The canonical merchant URL
            context: Click context (user, row, etc.)
        
        Returns:
            ResolvedLink with final_url and handler info
        """
        # Find handler for this domain
        handler_name = self.domain_map.get(context.merchant_domain)
        
        if handler_name and handler_name in self.handlers:
            handler = self.handlers[handler_name]
            return handler.transform(url, context)
        
        # No matching handler, use default
        return self.default_handler.transform(url, context)
    
    def list_handlers(self) -> List[Dict]:
        """List all registered handlers (for admin UI)."""
        return [
            {
                "name": h.name,
                "domains": h.domains,
                "configured": self._is_configured(h),
            }
            for h in self.handlers.values()
        ]
    
    def _is_configured(self, handler: AffiliateHandler) -> bool:
        """Check if handler has required config (e.g., API keys)."""
        if isinstance(handler, AmazonAssociatesHandler):
            return bool(handler.tag)
        if isinstance(handler, EbayPartnerHandler):
            return bool(handler.campaign_id)
        return True


# Global singleton
link_resolver = LinkResolver()
```

- [ ] Create `affiliate.py` file
- [ ] Implement `AffiliateHandler` base class
- [ ] Implement `NoAffiliateHandler`
- [ ] Implement `AmazonAssociatesHandler`
- [ ] Implement `EbayPartnerHandler`
- [ ] Implement `LinkResolver`

**Test:** Unit tests for each handler

---

### Step 3.2: Integrate Resolver into Clickout Endpoint

**File:** `apps/backend/main.py`

```python
from affiliate import link_resolver, ClickContext

@app.get("/api/out")
async def clickout_redirect(
    url: str,
    row_id: Optional[int] = None,
    idx: int = 0,
    source: str = "unknown",
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # ... existing validation and user extraction ...
    
    # Extract merchant domain
    merchant_domain = extract_merchant_domain(url)
    
    # Build context for resolver
    context = ClickContext(
        user_id=user_id,
        row_id=row_id,
        offer_index=idx,
        source=source,
        merchant_domain=merchant_domain,
    )
    
    # Resolve affiliate link
    resolved = link_resolver.resolve(url, context)
    
    # Log the clickout event
    event = ClickoutEvent(
        user_id=user_id,
        session_id=session_id,
        row_id=row_id,
        offer_index=idx,
        canonical_url=url,
        final_url=resolved.final_url,
        merchant_domain=merchant_domain,
        handler_name=resolved.handler_name,
        affiliate_tag=resolved.affiliate_tag,
        source=source,
    )
    session.add(event)
    await session.commit()
    
    # Redirect to transformed URL
    return RedirectResponse(url=resolved.final_url, status_code=302)
```

- [ ] Import `link_resolver` and `ClickContext`
- [ ] Build `ClickContext` from request params
- [ ] Call `link_resolver.resolve()`
- [ ] Log `handler_name` and `affiliate_tag` in event
- [ ] Redirect to `final_url`

**Test:** Amazon/eBay URLs get affiliate tags added

---

### Step 3.3: Add Environment Variables

**File:** `.env.example` (and Railway/deployment config)

```bash
# Affiliate Configuration
AMAZON_AFFILIATE_TAG=buyanything-20
EBAY_CAMPAIGN_ID=1234567890
# Future: SKIMLINKS_API_KEY, RAKUTEN_TOKEN, etc.
```

- [ ] Document required env vars
- [ ] Add to `.env.example`
- [ ] Configure in Railway (production)

**Test:** Handlers pick up config from environment

---

### Step 3.4: Add Admin Endpoint to List Handlers

**File:** `apps/backend/main.py`

```python
@app.get("/admin/affiliate/handlers")
async def list_affiliate_handlers(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """List all registered affiliate handlers and their status."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return link_resolver.list_handlers()
```

- [ ] Add endpoint
- [ ] Return handler list with config status

**Test:** Endpoint returns handler info

---

### Step 3.5: Add Unit Tests for Handlers

**New File:** `apps/backend/tests/test_affiliate.py`

```python
import pytest
from affiliate import (
    AmazonAssociatesHandler, EbayPartnerHandler, NoAffiliateHandler,
    LinkResolver, ClickContext
)

@pytest.fixture
def context():
    return ClickContext(
        user_id=1,
        row_id=10,
        offer_index=0,
        source="test",
        merchant_domain="amazon.com",
    )

def test_amazon_handler_adds_tag(context):
    handler = AmazonAssociatesHandler(tag="test-20")
    result = handler.transform("https://amazon.com/dp/B08N5/", context)
    assert "tag=test-20" in result.final_url
    assert result.handler_name == "amazon_associates"
    assert result.rewrite_applied

def test_amazon_handler_no_tag_configured(context):
    handler = AmazonAssociatesHandler(tag="")
    result = handler.transform("https://amazon.com/dp/B08N5/", context)
    assert result.final_url == "https://amazon.com/dp/B08N5/"
    assert not result.rewrite_applied

def test_ebay_handler_adds_campaign(context):
    context.merchant_domain = "ebay.com"
    handler = EbayPartnerHandler(campaign_id="123456")
    result = handler.transform("https://ebay.com/itm/12345", context)
    assert "campid=123456" in result.final_url
    assert result.handler_name == "ebay_partner"

def test_resolver_routes_to_correct_handler(context):
    resolver = LinkResolver()
    result = resolver.resolve("https://amazon.com/dp/B08N5/", context)
    assert result.handler_name == "amazon_associates"

def test_resolver_fallback_to_default():
    context = ClickContext(
        user_id=1, row_id=10, offer_index=0,
        source="test", merchant_domain="randomshop.com"
    )
    resolver = LinkResolver()
    result = resolver.resolve("https://randomshop.com/product", context)
    assert result.handler_name == "none"
    assert result.final_url == "https://randomshop.com/product"
```

- [ ] Create test file
- [ ] Test each handler independently
- [ ] Test resolver routing
- [ ] Test fallback behavior

**Test:** `pytest tests/test_affiliate.py` passes

---

### Step 3.6: Document Adding New Handlers

**New File:** `docs/adding-affiliate-handlers.md`

```markdown
# Adding New Affiliate Handlers

## Quick Start

1. Create a new handler class in `apps/backend/affiliate.py`:

```python
class MyNetworkHandler(AffiliateHandler):
    def __init__(self):
        self.api_key = os.getenv("MYNETWORK_API_KEY", "")
    
    @property
    def name(self) -> str:
        return "my_network"
    
    @property
    def domains(self) -> List[str]:
        return ["merchant1.com", "merchant2.com"]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        # Your transformation logic here
        pass
```

2. Register in `LinkResolver._register_builtin_handlers()`:

```python
self.register(MyNetworkHandler())
```

3. Add env var to `.env.example` and production config

4. Add tests to `tests/test_affiliate.py`

## Handler Guidelines

- Always return a `ResolvedLink`, even on error
- Set `rewrite_applied=False` if transformation fails
- Include error info in `metadata` for debugging
- Test with real URLs before deploying
```

- [ ] Create documentation file

---

## Acceptance Criteria

- [ ] `affiliate.py` module with handler base class and registry
- [ ] Amazon Associates handler adds `tag` parameter
- [ ] eBay Partner handler adds `campid` parameter
- [ ] Unknown domains pass through unchanged (NoAffiliateHandler)
- [ ] Clickout events log which handler was used
- [ ] Admin can list handlers and see config status
- [ ] Unit tests pass for all handlers

---

## Audit Considerations

- **Handler Versioning:** Consider adding version field to track handler changes
- **Revenue Reconciliation:** `affiliate_tag` in ClickoutEvent enables matching with network reports
- **Configuration Audit:** Log when handlers are registered/configured

---

## Future Handlers (Phase 2+)

- [ ] **SkimlinksHandler** — Universal fallback for smaller merchants
- [ ] **RakutenHandler** — Major affiliate network
- [ ] **CJHandler** — Commission Junction
- [ ] **ShareASaleHandler** — Popular for mid-size merchants
- [ ] **ImpactHandler** — Modern affiliate platform

---

## Files Changed

| File | Action |
|------|--------|
| `apps/backend/affiliate.py` | **New** — Handler registry |
| `apps/backend/main.py` | Integrate resolver into `/api/out` |
| `apps/backend/tests/test_affiliate.py` | **New** — Unit tests |
| `.env.example` | Add affiliate config vars |
| `docs/adding-affiliate-handlers.md` | **New** — Documentation |
