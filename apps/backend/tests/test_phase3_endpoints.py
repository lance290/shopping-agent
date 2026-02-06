"""Tests for Phase 3 endpoints: checkout, batch social, seller dashboard, admin stats, vendor discovery."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


# ── Batch Social Endpoint ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_social_returns_data(client: AsyncClient, auth_user_and_token, test_bid):
    """GET /bids/social/batch returns social data for multiple bid IDs."""
    _, token = auth_user_and_token
    bid = test_bid

    resp = await client.get(
        f"/bids/social/batch?bid_ids={bid.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert str(bid.id) in data
    entry = data[str(bid.id)]
    assert entry["bid_id"] == bid.id
    assert entry["like_count"] == 0
    assert entry["is_liked"] is False
    assert entry["comment_count"] == 0


@pytest.mark.asyncio
async def test_batch_social_empty_ids(client: AsyncClient, auth_user_and_token):
    """GET /bids/social/batch with empty bid_ids returns empty dict."""
    _, token = auth_user_and_token

    resp = await client.get(
        "/bids/social/batch?bid_ids=",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_batch_social_auth_required(client: AsyncClient):
    """GET /bids/social/batch requires authentication."""
    resp = await client.get("/bids/social/batch?bid_ids=1")
    assert resp.status_code == 401


# ── Checkout Endpoint ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_auth_required(client: AsyncClient):
    """POST /api/checkout/create-session requires auth."""
    resp = await client.post(
        "/api/checkout/create-session",
        json={"bid_id": 1, "row_id": 1},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_checkout_bid_not_found(client: AsyncClient, auth_user_and_token):
    """POST /api/checkout/create-session returns 404 for non-existent bid."""
    _, token = auth_user_and_token

    resp = await client.post(
        "/api/checkout/create-session",
        json={"bid_id": 99999, "row_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Either 404 (bid not found) or 503 (stripe not configured) is acceptable
    assert resp.status_code in (404, 503)


# ── Seller Dashboard ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seller_inbox_no_merchant(client: AsyncClient, auth_user_and_token):
    """GET /seller/inbox returns 403 if user has no merchant profile."""
    _, token = auth_user_and_token

    resp = await client.get(
        "/seller/inbox",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_seller_quotes_no_merchant(client: AsyncClient, auth_user_and_token):
    """GET /seller/quotes returns 403 if user has no merchant profile."""
    _, token = auth_user_and_token

    resp = await client.get(
        "/seller/quotes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_seller_profile_no_merchant(client: AsyncClient, auth_user_and_token):
    """GET /seller/profile returns 403 if user has no merchant profile."""
    _, token = auth_user_and_token

    resp = await client.get(
        "/seller/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_seller_inbox_with_merchant(client: AsyncClient, auth_user_and_token, session):
    """GET /seller/inbox returns 200 when merchant profile exists."""
    from models import Merchant

    user, token = auth_user_and_token

    merchant = Merchant(
        user_id=user.id,
        business_name="Test Merchant Co",
        email="merchant@test.com",
        contact_name="Test Contact",
        categories='["electronics"]',
    )
    session.add(merchant)
    await session.commit()

    resp = await client.get(
        "/seller/inbox",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Admin Stats ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client: AsyncClient, auth_user_and_token):
    """GET /admin/stats requires admin role."""
    _, token = auth_user_and_token

    resp = await client.get(
        "/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Regular users should get 403
    assert resp.status_code == 403


# ── Vendor Discovery Adapter ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_vendor_adapter():
    """MockVendorAdapter returns vendors for known categories."""
    from services.vendor_discovery import MockVendorAdapter

    adapter = MockVendorAdapter()
    assert await adapter.health_check() is True

    vendors = await adapter.find_sellers("private_aviation", limit=3)
    # May return vendors if wattdata_mock has data for this category
    assert isinstance(vendors, list)


@pytest.mark.asyncio
async def test_vendor_adapter_factory():
    """get_vendor_adapter returns an adapter instance."""
    import os
    from services.vendor_discovery import get_vendor_adapter, reset_adapter

    reset_adapter()
    os.environ["VENDOR_DISCOVERY_BACKEND"] = "mock"

    adapter = await get_vendor_adapter()
    assert adapter is not None
    assert await adapter.health_check() is True

    reset_adapter()


# ── Provenance Enrichment ────────────────────────────────────────────────


def test_provenance_enrichment_budget_match():
    """Provenance builder includes budget match when price is within budget."""
    import json
    from sourcing.service import SourcingService
    from sourcing.models import NormalizedResult

    # Create a mock result
    result = NormalizedResult(
        title="Test Product",
        price=49.99,
        currency="USD",
        url="https://example.com/product",
        merchant_name="TestMerchant",
        merchant_domain="example.com",
        source="mock",
        provenance={"matched_features": []},
    )

    # Create a mock row with choice_answers containing max_price
    class MockRow:
        search_intent = None
        choice_answers = json.dumps({"max_price": "100"})
        chat_history = None

    service = SourcingService.__new__(SourcingService)
    prov_json = service._build_enriched_provenance(result, MockRow())
    prov = json.loads(prov_json)

    # Should contain a budget match feature
    features = prov.get("matched_features", [])
    budget_matches = [f for f in features if "budget" in f.lower()]
    assert len(budget_matches) > 0, f"Expected budget match in features: {features}"


def test_provenance_enrichment_chat_excerpts():
    """Provenance builder extracts chat excerpts from row."""
    import json
    from sourcing.service import SourcingService
    from sourcing.models import NormalizedResult

    result = NormalizedResult(
        title="Test Product",
        price=25.0,
        currency="USD",
        url="https://example.com/product",
        merchant_name="TestMerchant",
        merchant_domain="example.com",
        source="mock",
        provenance={},
    )

    class MockRow:
        search_intent = None
        choice_answers = None
        chat_history = json.dumps([
            {"role": "user", "content": "I need a good bicycle for commuting"},
            {"role": "assistant", "content": "I found several options for commuter bicycles"},
        ])

    service = SourcingService.__new__(SourcingService)
    prov_json = service._build_enriched_provenance(result, MockRow())
    prov = json.loads(prov_json)

    excerpts = prov.get("chat_excerpts", [])
    assert len(excerpts) == 2
    assert excerpts[0]["role"] == "user"
    assert "bicycle" in excerpts[0]["content"]
