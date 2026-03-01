"""Tests for Pop swap/coupon provider scaffolding."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models.coupons import PopSwap, PopSwapClaim
from services.coupon_provider import (
    ManualProvider,
    HomeBrewProvider,
    IbottaProvider,
    AggregateProvider,
    SwapOffer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(name="sample_swap")
async def sample_swap_fixture(session: AsyncSession):
    """A sample active swap offer in the pop_swap table."""
    swap = PopSwap(
        category="steak sauce",
        target_product="A1 Steak Sauce",
        swap_product_name="Heinz 57 Sauce",
        offer_type="coupon",
        savings_cents=250,
        offer_description="Save $2.50 on Heinz 57 Sauce",
        brand_name="Heinz",
        provider="manual",
        is_active=True,
    )
    session.add(swap)
    await session.commit()
    await session.refresh(swap)
    return swap


@pytest_asyncio.fixture(name="expired_swap")
async def expired_swap_fixture(session: AsyncSession):
    """An expired swap offer."""
    swap = PopSwap(
        category="milk",
        target_product="Whole Milk",
        swap_product_name="Almond Breeze",
        offer_type="coupon",
        savings_cents=100,
        brand_name="Blue Diamond",
        provider="manual",
        is_active=True,
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    session.add(swap)
    await session.commit()
    await session.refresh(swap)
    return swap


@pytest_asyncio.fixture(name="homebrew_swap")
async def homebrew_swap_fixture(session: AsyncSession):
    """A homebrew (brand self-serve) swap offer."""
    swap = PopSwap(
        category="eggs",
        target_product="Store Brand Eggs",
        swap_product_name="Happy Egg Co Free Range",
        offer_type="rebate",
        savings_cents=150,
        offer_description="$1.50 rebate on Happy Egg Co",
        brand_name="Happy Egg Co",
        provider="homebrew",
        is_active=True,
        max_redemptions=100,
        current_redemptions=5,
    )
    session.add(swap)
    await session.commit()
    await session.refresh(swap)
    return swap


# ---------------------------------------------------------------------------
# CouponProvider unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_provider_finds_active_swap(session: AsyncSession, sample_swap):
    """ManualProvider returns active swaps matching category."""
    provider = ManualProvider()
    results = await provider.search_swaps("steak sauce", session=session)
    assert len(results) >= 1
    assert any(o.swap_product_name == "Heinz 57 Sauce" for o in results)


@pytest.mark.asyncio
async def test_manual_provider_excludes_expired(session: AsyncSession, sample_swap, expired_swap):
    """ManualProvider does not return expired swaps."""
    provider = ManualProvider()
    results = await provider.search_swaps("milk", session=session)
    assert not any(o.swap_product_name == "Almond Breeze" for o in results)


@pytest.mark.asyncio
async def test_manual_provider_empty_for_no_match(session: AsyncSession, sample_swap):
    """ManualProvider returns empty list for non-matching category."""
    provider = ManualProvider()
    results = await provider.search_swaps("frozen pizza", session=session)
    assert results == []


@pytest.mark.asyncio
async def test_homebrew_provider_finds_swap(session: AsyncSession, homebrew_swap):
    """HomeBrewProvider returns active homebrew swaps."""
    provider = HomeBrewProvider()
    results = await provider.search_swaps("eggs", session=session)
    assert len(results) >= 1
    assert results[0].swap_product_name == "Happy Egg Co Free Range"
    assert results[0].provider == "homebrew"


@pytest.mark.asyncio
async def test_homebrew_provider_respects_max_redemptions(session: AsyncSession):
    """HomeBrewProvider excludes fully redeemed offers."""
    swap = PopSwap(
        category="bread",
        swap_product_name="Dave's Killer Bread",
        offer_type="coupon",
        savings_cents=100,
        provider="homebrew",
        is_active=True,
        max_redemptions=10,
        current_redemptions=10,  # fully redeemed
    )
    session.add(swap)
    await session.commit()

    provider = HomeBrewProvider()
    results = await provider.search_swaps("bread", session=session)
    assert not any(o.swap_product_name == "Dave's Killer Bread" for o in results)


@pytest.mark.asyncio
async def test_ibotta_provider_raises_not_implemented():
    """IbottaProvider raises NotImplementedError (stub)."""
    provider = IbottaProvider()
    with pytest.raises(NotImplementedError, match="enterprise partnership"):
        await provider.search_swaps("milk")


@pytest.mark.asyncio
async def test_aggregate_provider_merges_results(session: AsyncSession, sample_swap, homebrew_swap):
    """AggregateProvider returns results from all providers, sorted by savings."""
    provider = AggregateProvider()
    results = await provider.search_swaps("", session=session)
    # Should find both swaps (empty category matches via ilike '%')
    names = [o.swap_product_name for o in results]
    assert "Heinz 57 Sauce" in names
    assert "Happy Egg Co Free Range" in names
    # Highest savings first
    if len(results) >= 2:
        assert results[0].savings_cents >= results[1].savings_cents


@pytest.mark.asyncio
async def test_aggregate_provider_skips_ibotta_gracefully(session: AsyncSession, sample_swap):
    """AggregateProvider skips IbottaProvider without crashing."""
    provider = AggregateProvider(providers=[ManualProvider(), IbottaProvider()])
    results = await provider.search_swaps("steak sauce", session=session)
    assert len(results) >= 1  # manual provider still works


@pytest.mark.asyncio
async def test_swap_offer_to_dict():
    """SwapOffer.to_dict() returns properly formatted data."""
    offer = SwapOffer(
        swap_id=1,
        category="milk",
        target_product="Whole Milk",
        swap_product_name="Oat Milk",
        offer_type="coupon",
        savings_cents=175,
        provider="manual",
    )
    d = offer.to_dict()
    assert d["savings_display"] == "$1.75"
    assert d["provider"] == "manual"
    assert d["swap_id"] == 1


# ---------------------------------------------------------------------------
# Admin API routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_swap_via_api(client: AsyncClient, session: AsyncSession):
    """POST /pop/admin/swaps creates a new swap offer."""
    resp = await client.post("/pop/admin/swaps", json={
        "category": "cereal",
        "swap_product_name": "Magic Spoon",
        "savings_cents": 200,
        "brand_name": "Magic Spoon",
        "offer_description": "Save $2 on Magic Spoon cereal",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "cereal"
    assert data["swap_product_name"] == "Magic Spoon"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_swaps_via_api(client: AsyncClient, session: AsyncSession, sample_swap):
    """GET /pop/admin/swaps returns active swaps."""
    resp = await client.get("/pop/admin/swaps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(s["swap_product_name"] == "Heinz 57 Sauce" for s in data["swaps"])


@pytest.mark.asyncio
async def test_list_swaps_filter_by_category(client: AsyncClient, session: AsyncSession, sample_swap):
    """GET /pop/admin/swaps?category=steak returns matching swaps."""
    resp = await client.get("/pop/admin/swaps?category=steak")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_list_swaps_filter_by_provider(client: AsyncClient, session: AsyncSession, sample_swap, homebrew_swap):
    """GET /pop/admin/swaps?provider=homebrew filters by provider."""
    resp = await client.get("/pop/admin/swaps?provider=homebrew")
    assert resp.status_code == 200
    data = resp.json()
    for s in data["swaps"]:
        assert s["provider"] == "homebrew"


@pytest.mark.asyncio
async def test_update_swap_via_api(client: AsyncClient, session: AsyncSession, sample_swap):
    """PATCH /pop/admin/swaps/{id} updates a swap offer."""
    resp = await client.patch(f"/pop/admin/swaps/{sample_swap.id}", json={
        "savings_cents": 300,
        "offer_description": "Now save $3!",
    })
    assert resp.status_code == 200
    assert resp.json()["updated"] is True

    # Verify update persisted
    await session.refresh(sample_swap)
    assert sample_swap.savings_cents == 300


@pytest.mark.asyncio
async def test_deactivate_swap_via_api(client: AsyncClient, session: AsyncSession, sample_swap):
    """DELETE /pop/admin/swaps/{id} soft-deactivates a swap."""
    resp = await client.delete(f"/pop/admin/swaps/{sample_swap.id}")
    assert resp.status_code == 200
    assert resp.json()["deactivated"] is True

    await session.refresh(sample_swap)
    assert sample_swap.is_active is False


@pytest.mark.asyncio
async def test_search_swaps_endpoint(client: AsyncClient, session: AsyncSession, sample_swap):
    """POST /pop/swaps/search returns matching offers via AggregateProvider."""
    resp = await client.post("/pop/swaps/search", json={
        "category": "steak sauce",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(o["swap_product_name"] == "Heinz 57 Sauce" for o in data["offers"])


@pytest.mark.asyncio
async def test_search_swaps_no_results(client: AsyncClient, session: AsyncSession):
    """POST /pop/swaps/search returns empty for no matches."""
    resp = await client.post("/pop/swaps/search", json={
        "category": "nuclear submarine parts",
    })
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
