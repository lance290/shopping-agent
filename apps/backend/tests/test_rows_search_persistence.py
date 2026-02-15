import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import selectinload
from sqlmodel import select
from models import Row, Bid, Seller
from sourcing.service import SourcingService
from sourcing.models import NormalizedResult, ProviderStatusSnapshot
from sourcing.repository import SourcingRepository, SearchResultWithStatus

@pytest.mark.asyncio
async def test_search_and_persist_creates_new_bids(session, test_user):
    # Setup
    row = Row(title="Test Row", user_id=test_user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    mock_repo = MagicMock(spec=SourcingRepository)
    normalized_results = [
        NormalizedResult(
            title="Item 1",
            url="http://example.com/1",
            source="test_provider",
            price=10.0,
            currency="USD",
            merchant_name="Merchant A",
            merchant_domain="merchant-a.com",
            canonical_url="http://example.com/1/canonical"
        )
    ]
    search_response = SearchResultWithStatus(
        results=[], # Raw results not used when normalized present
        normalized_results=normalized_results,
        provider_statuses=[
            ProviderStatusSnapshot(provider_id="test_provider", status="ok", result_count=1)
        ]
    )
    mock_repo.search_all_with_status = AsyncMock(return_value=search_response)

    service = SourcingService(session, mock_repo)

    # Execute
    bids, statuses, user_message = await service.search_and_persist(row.id, "query")

    # Verify
    assert len(bids) == 1
    assert bids[0].row_id == row.id
    assert bids[0].canonical_url == "http://example.com/1/canonical"
    assert bids[0].price == 10.0
    
    # Check DB
    stmt = select(Bid).where(Bid.row_id == row.id).options(selectinload(Bid.seller))
    db_bids = (await session.exec(stmt)).all()
    assert len(db_bids) == 1
    assert db_bids[0].seller.name == "Merchant A"

@pytest.mark.asyncio
async def test_search_and_persist_updates_existing_bids(session, test_user):
    # Setup
    row = Row(title="Test Row Update", user_id=test_user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    
    # Create existing seller and bid
    seller = Seller(name="Merchant A", domain="merchant-a.com")
    session.add(seller)
    await session.commit()
    
    existing_bid = Bid(
        row_id=row.id,
        vendor_id=seller.id,
        price=10.0,
        total_cost=10.0,
        currency="USD",
        item_title="Item 1 Old Title",
        item_url="http://example.com/1",
        source="test_provider",
        canonical_url="http://example.com/1/canonical",
        is_selected=True
    )
    session.add(existing_bid)
    await session.commit()

    mock_repo = MagicMock(spec=SourcingRepository)
    # New result with same canonical URL but different price/title
    normalized_results = [
        NormalizedResult(
            title="Item 1 New Title",
            url="http://example.com/1?ref=new",
            source="test_provider",
            price=12.0,
            currency="USD",
            merchant_name="Merchant A",
            merchant_domain="merchant-a.com",
            canonical_url="http://example.com/1/canonical"
        )
    ]
    search_response = SearchResultWithStatus(
        normalized_results=normalized_results,
        provider_statuses=[
            ProviderStatusSnapshot(provider_id="test_provider", status="ok", result_count=1)
        ]
    )
    mock_repo.search_all_with_status = AsyncMock(return_value=search_response)

    service = SourcingService(session, mock_repo)

    # Execute
    bids, statuses, user_message = await service.search_and_persist(row.id, "query")

    # Verify
    assert len(bids) == 1
    assert bids[0].id == existing_bid.id  # Same ID
    assert bids[0].price == 12.0
    assert bids[0].item_title == "Item 1 New Title"
    
    # Check DB count didn't increase
    db_bids = (await session.exec(select(Bid).where(Bid.row_id == row.id))).all()
    assert len(db_bids) == 1
    assert db_bids[0].price == 12.0

@pytest.mark.asyncio
async def test_search_and_persist_deduplicates_by_canonical(session, test_user):
    # Setup
    row = Row(title="Test Row Dedup", user_id=test_user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    mock_repo = MagicMock(spec=SourcingRepository)
    # Two results pointing to same canonical URL
    normalized_results = [
        NormalizedResult(
            title="Item A Var 1",
            url="http://example.com/a?v=1",
            source="p1",
            price=10.0,
            currency="USD",
            merchant_name="M",
            merchant_domain="m.com",
            canonical_url="http://example.com/a"
        ),
        NormalizedResult(
            title="Item A Var 2",
            url="http://example.com/a?v=2",
            source="p2",
            price=10.0,
            currency="USD",
            merchant_name="M",
            merchant_domain="m.com",
            canonical_url="http://example.com/a"
        )
    ]
    search_response = SearchResultWithStatus(
        normalized_results=normalized_results,
        provider_statuses=[]
    )
    mock_repo.search_all_with_status = AsyncMock(return_value=search_response)

    service = SourcingService(session, mock_repo)

    # Execute
    bids, statuses, user_message = await service.search_and_persist(row.id, "query")

    # Verify
    # Should result in 1 bid because they share canonical_url
    # logic in service: "if new_bid.canonical_url: bids_by_canonical[new_bid.canonical_url] = new_bid"
    # The first one creates it, the second one updates it (or just sees it exists in the map)
    
    db_bids = (await session.exec(select(Bid).where(Bid.row_id == row.id))).all()
    assert len(db_bids) == 1
    assert db_bids[0].canonical_url == "http://example.com/a"
