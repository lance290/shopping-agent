# PRD: WattData MCP Integration

**Phase:** 3 — Closing the Loop  
**Priority:** P0  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

Vendor discovery currently runs against `services/wattdata_mock.py` — 11 hardcoded charter aviation providers. The outreach loop (discover vendors → send RFP → receive quotes → display as tiles) is architecturally complete but **cannot function beyond private aviation** because there is no real vendor data source.

The WattData MCP server is expected online in **~2 weeks**. The exact API surface is unknown, but the working assumption is:

- **Sellers** can use it to find ICPs (Ideal Customer Profiles) — i.e., discover buyer requests that match their offerings.
- **Buyers** can use it to find sellers — i.e., discover vendors for a given category/need.

This PRD prepares the integration so we can connect quickly once the MCP is live, while keeping the mock as a fallback.

---

## 2. Solution Overview

Build an **adapter layer** that abstracts vendor discovery behind a common interface. The adapter supports multiple backends:

1. **Mock** (current) — `wattdata_mock.py`, used for development and fallback.
2. **WattData MCP** — real vendor data, connected when available.
3. **Manual** — admin-curated vendor lists (future).

The adapter is called from `outreach.py` and the vendor tile feature. When WattData MCP goes live, we swap the default backend without changing any calling code.

---

## 3. Design Principles

Given the unknown API shape, the design must be:

- **Adapter-pattern:** All vendor discovery goes through a `VendorDiscovery` interface. Implementations are swappable.
- **Graceful degradation:** If WattData is unavailable, fall back to mock data with a log warning.
- **Schema-flexible:** The adapter normalizes WattData responses into our existing `Vendor` dataclass. Unknown fields are preserved in a `raw_data` dict for future use.
- **Bidirectional:** Support both "find sellers for this buyer need" and "find buyer needs for this seller" when the MCP supports it.

---

## 4. Scope

### In Scope
- `VendorDiscoveryAdapter` interface with `find_sellers()` and `find_buyers()` methods
- WattData MCP client implementation
- Configuration to switch between mock/live backends
- Error handling and fallback logic
- Seller-side: surface buyer RFPs that match a seller's profile (feeds into PRD-03 Seller Dashboard)
- Buyer-side: replace mock vendor tiles with WattData results
- Logging and observability for MCP calls

### Out of Scope
- Modifying the WattData MCP server itself
- Real-time streaming from WattData (batch fetch is fine for v1)
- WattData authentication/billing (assume API key or MCP connection string)

---

## 5. User Stories

**US-01:** As a buyer searching for "private jet charter LAX to Miami", I want to see real charter companies (from WattData) as vendor tiles so I can request quotes from actual providers.

**US-02:** As a seller registered on the platform, I want to be notified when a buyer posts an RFP matching my categories so I can proactively submit a quote.

**US-03:** As the system, I want to fall back to mock vendors when WattData is unreachable so the user experience doesn't break.

**US-04:** As a developer, I want to switch between mock and live vendor backends via an environment variable so testing is easy.

---

## 6. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | `VendorDiscoveryAdapter` interface exists with `find_sellers(category, constraints)` and `find_buyers(seller_profile)` methods. |
| AC-02 | `WattDataAdapter` implements the interface and connects to the MCP server. |
| AC-03 | `MockAdapter` wraps the existing `wattdata_mock.py` and implements the same interface. |
| AC-04 | `VENDOR_DISCOVERY_BACKEND` env var controls which adapter is used (`mock` or `wattdata`). |
| AC-05 | If `wattdata` is selected but the MCP is unreachable, the system falls back to `mock` with a warning log. |
| AC-06 | WattData vendor results are normalized into the existing `Vendor` dataclass format. |
| AC-07 | Unknown/extra fields from WattData are preserved in `Vendor.raw_data` for future use. |
| AC-08 | Outreach trigger (`/outreach/rows/{row_id}/trigger`) works identically regardless of backend. |

---

## 7. Technical Design

### 7.1 Adapter Interface

```python
# services/vendor_discovery.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Vendor:
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    category: Optional[str] = None
    website: Optional[str] = None
    service_areas: Optional[List[str]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BuyerNeed:
    row_id: int
    title: str
    category: str
    choice_factors: Dict[str, Any]
    budget_max: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

class VendorDiscoveryAdapter(ABC):
    @abstractmethod
    async def find_sellers(
        self, category: str, constraints: Optional[Dict] = None, limit: int = 10
    ) -> List[Vendor]:
        """Find sellers/vendors matching a buyer's need."""
        ...

    @abstractmethod
    async def find_buyers(
        self, seller_profile: Dict[str, Any], limit: int = 10
    ) -> List[BuyerNeed]:
        """Find buyer needs matching a seller's profile (ICP matching)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is reachable."""
        ...
```

### 7.2 Mock Adapter

Wraps existing `wattdata_mock.py`:

```python
class MockVendorAdapter(VendorDiscoveryAdapter):
    async def find_sellers(self, category, constraints=None, limit=10):
        from services.wattdata_mock import get_vendors
        return [Vendor(**v.__dict__) for v in get_vendors(category, limit)]

    async def find_buyers(self, seller_profile, limit=10):
        # Mock: return empty (sellers can't discover buyers in mock mode)
        return []

    async def health_check(self):
        return True
```

### 7.3 WattData MCP Adapter

```python
class WattDataAdapter(VendorDiscoveryAdapter):
    def __init__(self):
        self.mcp_url = os.getenv("WATTDATA_MCP_URL")
        # Connection setup TBD when MCP API is known

    async def find_sellers(self, category, constraints=None, limit=10):
        # Call WattData MCP, normalize response to Vendor[]
        # Preserve unknown fields in raw_data
        ...

    async def find_buyers(self, seller_profile, limit=10):
        # Call WattData MCP for ICP matching
        # Normalize to BuyerNeed[]
        ...

    async def health_check(self):
        # Ping MCP health endpoint
        ...
```

### 7.4 Factory with Fallback

```python
def get_vendor_adapter() -> VendorDiscoveryAdapter:
    backend = os.getenv("VENDOR_DISCOVERY_BACKEND", "mock")
    if backend == "wattdata":
        adapter = WattDataAdapter()
        # Test connection, fall back if unreachable
        try:
            if not await adapter.health_check():
                raise ConnectionError("WattData MCP unreachable")
            return adapter
        except Exception as e:
            logger.warning(f"WattData unavailable, falling back to mock: {e}")
            return MockVendorAdapter()
    return MockVendorAdapter()
```

### 7.5 Integration Points

1. **`routes/outreach.py`** — Replace `from services.wattdata_mock import get_vendors` with adapter call.
2. **`routes/outreach.py` vendor endpoints** — `/vendors/{category}` uses adapter.
3. **Seller Dashboard (PRD-03)** — Uses `find_buyers()` to surface matching RFPs.

---

## 8. Environment Variables

| Variable | Description |
|----------|-------------|
| `VENDOR_DISCOVERY_BACKEND` | `mock` (default) or `wattdata` |
| `WATTDATA_MCP_URL` | MCP server connection URL (required if backend=wattdata) |
| `WATTDATA_API_KEY` | API key if required by MCP (TBD) |

---

## 9. Phased Rollout

### Phase 3a (Now — before MCP is live)
- Build adapter interface and mock implementation
- Refactor `outreach.py` to use adapter
- Write integration tests with mock adapter
- Scaffold `WattDataAdapter` with placeholder methods

### Phase 3b (When MCP goes live)
- Implement `WattDataAdapter.find_sellers()` based on actual MCP API
- Implement `WattDataAdapter.find_buyers()` if available
- Test with real data
- Flip `VENDOR_DISCOVERY_BACKEND=wattdata` in production

### Phase 3c (Post-launch polish)
- Add caching layer for WattData responses (TTL-based)
- Implement rate limiting for MCP calls
- Add vendor quality scoring based on response rates
- Expand to additional categories beyond private aviation

---

## 10. Open Questions (Resolve When MCP Is Live)

| # | Question | Impact |
|---|----------|--------|
| 1 | What is the MCP API shape? REST? GraphQL? Tool calls? | Determines adapter implementation |
| 2 | Does the MCP support filtering by category/location/budget? | Determines how much filtering we do client-side |
| 3 | Does the MCP provide seller contact info directly? | May affect outreach flow |
| 4 | Is there rate limiting on the MCP? | Determines caching strategy |
| 5 | Can sellers push their profile to WattData, or is it pull-only? | Affects seller onboarding flow |
| 6 | Does the MCP support ICP matching (find buyers for a seller)? | Determines seller dashboard capabilities |

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| MCP API shape is radically different from assumptions | Adapter pattern isolates changes to one file |
| MCP launch delayed beyond 2 weeks | Mock adapter keeps the product functional |
| MCP data quality is poor | Add vendor quality scoring; let users flag bad vendors |
| MCP goes down in production | Auto-fallback to mock with monitoring alert |

---

## 12. Implementation Checklist

- [ ] Create `services/vendor_discovery.py` with adapter interface
- [ ] Implement `MockVendorAdapter` wrapping existing mock
- [ ] Scaffold `WattDataAdapter` with placeholder methods
- [ ] Create `get_vendor_adapter()` factory function
- [ ] Refactor `routes/outreach.py` to use adapter
- [ ] Refactor `/vendors/{category}` endpoint to use adapter
- [ ] Add `VENDOR_DISCOVERY_BACKEND` env var to `.env.example`
- [ ] Write unit tests for mock adapter
- [ ] Write integration tests for adapter fallback behavior
- [ ] (Phase 3b) Implement WattData MCP client when API is known
- [ ] (Phase 3b) End-to-end test with real WattData data
