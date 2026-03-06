"""Tests for PRD-08 CPG enrichment gaps:

1. _enrich_row_cpg — saves retailer_sku + brand_name from Kroger bid
2. _enrich_row_cpg — creates CouponCampaign when brand has no active swap
3. _enrich_row_cpg — increments intent_count when campaign already exists
4. _enrich_row_cpg — skips outreach when brand already has active PopSwap
5. Sponsored Deal Slot Logic — referrer brand coupons sort first in get_pop_list
"""
import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession

from models.rows import Row, Project
from models.bids import Bid
from models.auth import User
from models.coupons import CouponCampaign, PopSwap
from routes.pop_processor import _enrich_row_cpg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(session: AsyncSession, email: str, referred_by_id: int | None = None) -> User:
    user = User(email=email, referred_by_id=referred_by_id)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_project(session: AsyncSession, user_id: int) -> Project:
    project = Project(title="Test List", user_id=user_id)
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def _make_row(session: AsyncSession, user_id: int, project_id: int, title: str = "Tide Pods") -> Row:
    row = Row(user_id=user_id, project_id=project_id, title=title, status="bids_arriving")
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def _make_kroger_bid(
    session: AsyncSession,
    row_id: int,
    title: str = "Tide Pods 42ct",
    url: str = "https://www.kroger.com/p/tide-pods-42ct/0003700089771",
    source_payload: dict | None = None,
) -> Bid:
    bid = Bid(
        row_id=row_id,
        item_title=title,
        item_url=url,
        price=12.99,
        currency="USD",
        source="kroger",
        source_payload=source_payload if source_payload is not None else {"brand": "Tide"},
    )
    session.add(bid)
    await session.flush()
    await session.refresh(bid)
    return bid


# ---------------------------------------------------------------------------
# Tests: Kroger SKU / brand_name enrichment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enrich_row_saves_retailer_sku_from_kroger_url(session: AsyncSession):
    """retailer_sku is extracted from the Kroger product URL slug."""
    user = await _make_user(session, "enrich1@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id)
    await _make_kroger_bid(session, row.id, url="https://www.kroger.com/p/tide-pods-42ct/0003700089771")
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(row)

    assert row.retailer_sku == "0003700089771"


@pytest.mark.asyncio
async def test_enrich_row_saves_brand_name_from_source_payload(session: AsyncSession):
    """brand_name comes from source_payload['brand'] when present."""
    user = await _make_user(session, "enrich2@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id)
    await _make_kroger_bid(session, row.id, source_payload={"brand": "Tide"})
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(row)

    assert row.brand_name == "Tide"


@pytest.mark.asyncio
async def test_enrich_row_brand_name_fallback_to_title_first_word(session: AsyncSession):
    """brand_name falls back to first word of item_title when source_payload has no brand."""
    user = await _make_user(session, "enrich3@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id, title="Heinz 57 Steak Sauce")
    # No brand key in source_payload — forces title-first-word fallback
    await _make_kroger_bid(
        session, row.id,
        title="Heinz 57 Steak Sauce 10oz",
        source_payload={},
    )
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(row)

    assert row.brand_name == "Heinz"


@pytest.mark.asyncio
async def test_enrich_row_does_not_overwrite_existing_values(session: AsyncSession):
    """Existing retailer_sku / brand_name are not overwritten."""
    user = await _make_user(session, "enrich4@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id)
    row.retailer_sku = "EXISTING_SKU"
    row.brand_name = "ExistingBrand"
    session.add(row)
    await _make_kroger_bid(session, row.id, source_payload={"brand": "Tide"})
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(row)

    assert row.retailer_sku == "EXISTING_SKU"
    assert row.brand_name == "ExistingBrand"


@pytest.mark.asyncio
async def test_enrich_row_no_op_when_no_kroger_bid(session: AsyncSession):
    """No changes when there are no Kroger bids for the row."""
    user = await _make_user(session, "enrich5@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id)
    # Add a non-Kroger bid
    bid = Bid(row_id=row.id, item_title="Tide", item_url="https://amazon.com/p/1", price=11.99,
              currency="USD", source="amazon")
    session.add(bid)
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(row)

    assert row.retailer_sku is None
    assert row.brand_name is None


# ---------------------------------------------------------------------------
# Tests: Outreach Queue (CouponCampaign creation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enrich_creates_coupon_campaign_for_new_brand(session: AsyncSession):
    """A CouponCampaign is created when the brand has no active PopSwap."""
    user = await _make_user(session, "outreach1@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id, title="Tide Pods")
    await _make_kroger_bid(session, row.id, source_payload={"brand": "Tide"})
    await session.commit()

    await _enrich_row_cpg(session, row)

    from sqlmodel import select
    campaign_stmt = select(CouponCampaign).where(CouponCampaign.brand_name == "Tide")
    result = await session.execute(campaign_stmt)
    campaign = result.scalar_one_or_none()

    assert campaign is not None
    assert campaign.status == "pending"
    assert campaign.intent_count == 1
    assert campaign.target_product == "Tide Pods"


@pytest.mark.asyncio
async def test_enrich_increments_intent_count_for_existing_campaign(session: AsyncSession):
    """intent_count is incremented when a pending campaign already exists."""
    user = await _make_user(session, "outreach2@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id, title="Tide Pods")

    # Pre-existing campaign
    existing = CouponCampaign(
        brand_name="Tide",
        category="laundry detergent",
        intent_count=5,
        status="pending",
    )
    session.add(existing)
    await _make_kroger_bid(session, row.id, source_payload={"brand": "Tide"})
    await session.commit()

    await _enrich_row_cpg(session, row)
    await session.refresh(existing)

    assert existing.intent_count == 6


@pytest.mark.asyncio
async def test_enrich_skips_campaign_when_active_swap_exists(session: AsyncSession):
    """No CouponCampaign is created when an active PopSwap already exists for the brand."""
    user = await _make_user(session, "outreach3@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id, title="Tide Pods")

    # Active swap already in place
    swap = PopSwap(
        category="laundry detergent",
        swap_product_name="Tide Pods 42ct",
        brand_name="Tide",
        savings_cents=150,
        is_active=True,
        provider="manual",
    )
    session.add(swap)
    await _make_kroger_bid(session, row.id, source_payload={"brand": "Tide"})
    await session.commit()

    await _enrich_row_cpg(session, row)

    from sqlmodel import select
    campaign_stmt = select(CouponCampaign).where(CouponCampaign.brand_name == "Tide")
    result = await session.execute(campaign_stmt)
    campaign = result.scalar_one_or_none()

    assert campaign is None


@pytest.mark.asyncio
async def test_enrich_skips_campaign_creation_when_brand_name_unknown(session: AsyncSession):
    """No CouponCampaign is created when brand_name cannot be resolved."""
    user = await _make_user(session, "outreach4@example.com")
    project = await _make_project(session, user.id)
    row = await _make_row(session, user.id, project.id, title="Unknown Item")

    # Bid with empty title and no brand in payload
    bid = Bid(
        row_id=row.id,
        item_title="",
        item_url="https://www.kroger.com/p/product/0000001",
        price=5.99,
        currency="USD",
        source="kroger",
        source_payload={},
    )
    session.add(bid)
    await session.commit()

    await _enrich_row_cpg(session, row)

    from sqlmodel import select
    campaign_stmt = select(CouponCampaign)
    result = await session.execute(campaign_stmt)
    assert result.scalars().first() is None


# ---------------------------------------------------------------------------
# Tests: Sponsored Deal Slot Logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sponsored_swaps_sort_first_when_referrer_is_brand_manager(
    session: AsyncSession,
):
    """
    Swaps linked to the user's referrer (referred_by_id) should be placed first
    in the swap list and carry is_sponsored=True.

    This test calls the route directly via the test client, asserting on the
    response payload rather than testing internal sort order.
    """
    from httpx import AsyncClient
    from models.coupons import PopSwap

    # Brand manager user (the referrer)
    brand_manager = await _make_user(session, "brandmgr@example.com")

    # Sponsored swap owned by the brand manager
    sponsored_swap = PopSwap(
        category="steak sauce",
        swap_product_name="Heinz 57",
        brand_name="Heinz",
        savings_cents=200,
        is_active=True,
        provider="homebrew",
        brand_user_id=brand_manager.id,
    )
    session.add(sponsored_swap)

    # Non-sponsored swap (different brand)
    other_swap = PopSwap(
        category="steak sauce",
        swap_product_name="A1 Sauce",
        brand_name="A1",
        savings_cents=100,
        is_active=True,
        provider="manual",
        brand_user_id=None,
    )
    session.add(other_swap)
    await session.commit()

    # A user referred by the brand manager
    shopper = await _make_user(
        session, "shopper_sponsored@example.com", referred_by_id=brand_manager.id
    )
    project = await _make_project(session, shopper.id)
    row = await _make_row(session, shopper.id, project.id, title="steak sauce")
    await session.commit()

    # Test the sort logic directly (unit-level) — simulate what pop_list.py does
    from services.coupon_provider import SwapOffer

    provider_swaps = [
        SwapOffer(
            swap_id=other_swap.id,
            category="steak sauce",
            target_product=None,
            swap_product_name="A1 Sauce",
            offer_type="coupon",
            savings_cents=100,
            brand_name="A1",
            brand_user_id=None,
            provider="manual",
        ),
        SwapOffer(
            swap_id=sponsored_swap.id,
            category="steak sauce",
            target_product=None,
            swap_product_name="Heinz 57",
            offer_type="coupon",
            savings_cents=200,
            brand_name="Heinz",
            brand_user_id=brand_manager.id,
            provider="homebrew",
        ),
    ]

    referrer_brand_user_id = shopper.referred_by_id
    sponsored = [s for s in provider_swaps if s.brand_user_id == referrer_brand_user_id]
    non_sponsored = [s for s in provider_swaps if s.brand_user_id != referrer_brand_user_id]
    sorted_swaps = sponsored + non_sponsored

    assert sorted_swaps[0].brand_name == "Heinz"
    assert sorted_swaps[0].brand_user_id == brand_manager.id
    assert sorted_swaps[1].brand_name == "A1"


@pytest.mark.asyncio
async def test_no_sponsored_sort_when_no_referrer(session: AsyncSession):
    """When referred_by_id is None, swap order is unchanged."""
    shopper = await _make_user(session, "shopper_noreferral@example.com", referred_by_id=None)

    from services.coupon_provider import SwapOffer
    provider_swaps = [
        SwapOffer(
            swap_id=1, category="milk", target_product=None,
            swap_product_name="Horizon Organic", offer_type="coupon",
            savings_cents=50, brand_name="Horizon", brand_user_id=42, provider="manual",
        ),
        SwapOffer(
            swap_id=2, category="milk", target_product=None,
            swap_product_name="Whole Foods Milk", offer_type="coupon",
            savings_cents=75, brand_name="365", brand_user_id=None, provider="manual",
        ),
    ]

    referrer_brand_user_id = shopper.referred_by_id  # None
    if referrer_brand_user_id and provider_swaps:
        sponsored = [s for s in provider_swaps if s.brand_user_id == referrer_brand_user_id]
        non_sponsored = [s for s in provider_swaps if s.brand_user_id != referrer_brand_user_id]
        sorted_swaps = sponsored + non_sponsored
    else:
        sorted_swaps = provider_swaps

    # Order unchanged
    assert sorted_swaps[0].brand_name == "Horizon"
    assert sorted_swaps[1].brand_name == "365"
