"""Tests for Pop brand portal routes (PRD-08: Coupon Network).

Covers:
  - POST /pop/brands/campaigns — create campaign + magic link
  - GET  /pop/brands/claim?token=XYZ — verify token
  - POST /pop/brands/claim — submit coupon (creates PopSwap)
  - Token expiry, reuse, and invalid token handling
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models.coupons import CouponCampaign, BrandPortalToken, PopSwap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(name="campaign_with_token")
async def campaign_with_token_fixture(session: AsyncSession):
    """Create a campaign and portal token for testing."""
    campaign = CouponCampaign(
        brand_name="Tide",
        brand_contact_email="pm@pgcom.example",
        category="laundry detergent",
        target_product="Tide Pods 42ct",
        intent_count=500,
        status="pending",
    )
    session.add(campaign)
    await session.flush()

    token = BrandPortalToken(
        campaign_id=campaign.id,
        brand_email="pm@pgcom.example",
    )
    session.add(token)
    await session.commit()
    await session.refresh(campaign)
    await session.refresh(token)
    return campaign, token


# ---------------------------------------------------------------------------
# Campaign creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient):
    """POST /pop/brands/campaigns creates a campaign and returns a portal URL."""
    resp = await client.post("/pop/brands/campaigns", json={
        "brand_name": "Heinz",
        "brand_contact_email": "pm@heinz.example",
        "category": "ketchup",
        "target_product": "Heinz Ketchup 32oz",
        "intent_count": 200,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand_name"] == "Heinz"
    assert data["category"] == "ketchup"
    assert "token" in data
    assert "portal_url" in data
    assert data["portal_url"].startswith("https://popsavings.com/brands/claim?token=")


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_valid_token(client: AsyncClient, campaign_with_token):
    """GET /pop/brands/claim with valid token returns campaign info."""
    campaign, token = campaign_with_token
    resp = await client.get(f"/pop/brands/claim?token={token.token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["campaign"]["brand_name"] == "Tide"
    assert data["campaign"]["intent_count"] == 500


@pytest.mark.asyncio
async def test_verify_invalid_token(client: AsyncClient):
    """GET /pop/brands/claim with bad token returns 404."""
    resp = await client.get("/pop/brands/claim?token=bogus_token_123")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_expired_token(client: AsyncClient, session: AsyncSession, campaign_with_token):
    """GET /pop/brands/claim with expired token returns 410."""
    _, token = campaign_with_token
    token.expires_at = datetime.utcnow() - timedelta(hours=1)
    session.add(token)
    await session.commit()

    resp = await client.get(f"/pop/brands/claim?token={token.token}")
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_verify_used_token(client: AsyncClient, session: AsyncSession, campaign_with_token):
    """GET /pop/brands/claim with used token returns 410."""
    _, token = campaign_with_token
    token.is_used = True
    session.add(token)
    await session.commit()

    resp = await client.get(f"/pop/brands/claim?token={token.token}")
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Coupon submission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_coupon(client: AsyncClient, session: AsyncSession, campaign_with_token):
    """POST /pop/brands/claim creates a PopSwap and marks token as used."""
    campaign, token = campaign_with_token
    resp = await client.post("/pop/brands/claim", json={
        "token": token.token,
        "swap_product_name": "Tide Pods 42ct",
        "savings_cents": 100,
        "offer_description": "Save $1.00 on Tide Pods",
        "swap_product_url": "https://tide.example.com/coupon",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["savings_display"] == "$1.00"

    # Verify token is marked as used
    await session.refresh(token)
    assert token.is_used is True

    # Verify campaign status updated
    await session.refresh(campaign)
    assert campaign.status == "claimed"
    assert campaign.swap_id == data["swap_id"]

    # Verify PopSwap was created
    swap = await session.get(PopSwap, data["swap_id"])
    assert swap is not None
    assert swap.provider == "homebrew"
    assert swap.brand_name == "Tide"
    assert swap.savings_cents == 100
    assert swap.is_active is True


@pytest.mark.asyncio
async def test_submit_coupon_zero_savings(client: AsyncClient, campaign_with_token):
    """POST /pop/brands/claim with savings_cents=0 returns 400."""
    _, token = campaign_with_token
    resp = await client.post("/pop/brands/claim", json={
        "token": token.token,
        "swap_product_name": "Free Product",
        "savings_cents": 0,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_coupon_reuse_token(client: AsyncClient, campaign_with_token):
    """POST /pop/brands/claim twice with same token fails on second attempt."""
    _, token = campaign_with_token
    # First submission
    resp1 = await client.post("/pop/brands/claim", json={
        "token": token.token,
        "swap_product_name": "Tide Pods 42ct",
        "savings_cents": 100,
    })
    assert resp1.status_code == 200

    # Second submission with same token
    resp2 = await client.post("/pop/brands/claim", json={
        "token": token.token,
        "swap_product_name": "Another Product",
        "savings_cents": 50,
    })
    assert resp2.status_code == 410


@pytest.mark.asyncio
async def test_submit_coupon_invalid_token(client: AsyncClient):
    """POST /pop/brands/claim with invalid token returns 404."""
    resp = await client.post("/pop/brands/claim", json={
        "token": "totally_fake_token",
        "swap_product_name": "Something",
        "savings_cents": 100,
    })
    assert resp.status_code == 404
