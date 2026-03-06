import pytest
import inspect
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Row, Bid, Seller, RequestSpec
from database import engine
from startup_migrations import run_startup_migrations

@pytest.mark.asyncio
async def test_search_architecture_v2_columns_exist(session: AsyncSession):
    """Verify that the new columns for Search Architecture v2 exist in the database."""
    # Check 'row' table columns
    result = await session.exec(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'row' AND column_name IN ('search_intent', 'provider_query_map', 'origin_channel', 'origin_message_id', 'origin_user_id')"
        )
    )
    columns = result.all()
    column_names = [col[0] for col in columns]
    assert "search_intent" in column_names
    assert "provider_query_map" in column_names
    assert "origin_channel" in column_names
    assert "origin_message_id" in column_names
    assert "origin_user_id" in column_names

    # Check 'bid' table columns
    result = await session.exec(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'bid' AND column_name IN "
            "('canonical_url', 'source_payload', 'search_intent_version', 'normalized_at')"
        )
    )
    columns = result.all()
    column_names = [col[0] for col in columns]
    assert "canonical_url" in column_names
    assert "source_payload" in column_names
    assert "search_intent_version" in column_names
    assert "normalized_at" in column_names

@pytest.mark.asyncio
async def test_persist_search_architecture_v2_fields(session: AsyncSession):
    """Verify we can persist data to the new fields."""
    # Create a test row with new fields
    # Use relationship for RequestSpec to ensure FK is handled correctly
    spec = RequestSpec(item_name="test", constraints="{}")
    row = Row(
        title="Migration Test Row",
        search_intent='{"product_category": "electronics"}',
        provider_query_map='{"rainforest": {"query": "test"}}',
        origin_channel="web",
        origin_message_id="msg-test-123",
        origin_user_id=42,
        request_spec=spec
    )
    session.add(row)
    # Use flush() to send to DB and verify constraints/types without committing transaction
    await session.flush()
    await session.refresh(row)

    assert row.search_intent == '{"product_category": "electronics"}'
    assert row.provider_query_map == '{"rainforest": {"query": "test"}}'
    assert row.origin_channel == "web"
    assert row.origin_message_id == "msg-test-123"
    assert row.origin_user_id == 42
    
    # Create a test bid with new fields
    # Need a seller first
    seller = Seller(name="Migration Test Seller")
    session.add(seller)
    await session.flush()
    await session.refresh(seller)
    
    bid = Bid(
        row_id=row.id,
        vendor_id=seller.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Item",
        canonical_url="https://example.com/item",
        source_payload={"raw": "data"},
        search_intent_version="v1",
    )
    session.add(bid)
    await session.flush()
    await session.refresh(bid)
    
    assert bid.canonical_url == "https://example.com/item"
    assert bid.source_payload == {"raw": "data"}
    assert bid.search_intent_version == "v1"
    assert bid.normalized_at is None # Default is None
    
    # No explicit cleanup needed if we don't commit (fixture handles rollback)


def test_startup_migrations_cover_row_origin_columns():
    source = inspect.getsource(run_startup_migrations)
    assert 'ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_channel VARCHAR;' in source
    assert 'ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_message_id VARCHAR;' in source
    assert 'ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_user_id INTEGER;' in source
