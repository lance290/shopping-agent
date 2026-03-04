"""Extracted vendor management e2e tests from test_e2e_revenue_flows.py."""
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Row, User, Vendor, AuthSession, Bid, Seller, SellerQuote, OutreachEvent, generate_session_token, hash_token, generate_magic_link_token
from services.sdui_builder import build_zero_results_schema


# ---------------------------------------------------------------------------
# Scenario 6: Outreach Unsubscribe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_vendor_unsubscribe(client, auth_user_and_token, session):
    """Vendor clicks unsubscribe link → opted out of future outreach."""
    user, _ = auth_user_and_token

    row = Row(title="Test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    token_val = generate_magic_link_token()
    event = OutreachEvent(
        row_id=row.id,
        vendor_email="vendor@example.com",
        vendor_company="TestCo",
        vendor_source="blast",
        quote_token=token_val,
        sent_at=datetime.utcnow(),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    resp = await client.get(f"/outreach/unsubscribe/{token_val}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsubscribed"

    await session.refresh(event)
    assert event.opt_out is True


# ---------------------------------------------------------------------------
# Scenario 7: Row CRUD + Search Integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_create_row_and_fetch(client, auth_user_and_token, session):
    """Create a row via API, then fetch it back."""
    user, token = auth_user_and_token

    # Create row
    resp = await client.post(
        "/rows",
        json={"title": "Standing desk", "status": "sourcing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    row_data = resp.json()
    row_id = row_data["id"]
    assert row_data["title"] == "Standing desk"

    # Fetch rows
    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    rows = resp.json()
    assert any(r["id"] == row_id for r in rows)


# ---------------------------------------------------------------------------
# Scenario 8: Health Check Flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_health_and_readiness(client, session):
    """Health and readiness endpoints respond correctly."""
    # Basic health (no DB needed)
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    # Readiness (checks DB)
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"


# ---------------------------------------------------------------------------
# Scenario 9: Clickout with Missing bid_id (Regression)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_clickout_without_bid_id(client):
    """Clickout works even when bid_id is not provided (common for eBay)."""
    resp = await client.get(
        "/api/out?url=https://www.ebay.com/itm/123456&row_id=1&source=ebay_browse",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "ebay.com" in location


# ---------------------------------------------------------------------------
# Scenario 10: Blast Outreach (Multiple Vendors)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_blast_outreach_dry_run(client, auth_user_and_token, session):
    """Blast dry run returns preview of emails that would be sent."""
    user, token = auth_user_and_token
    user.name = "Test User"
    user.email = "test@example.com"
    session.add(user)

    row = Row(title="Private jet charter", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create vendor + bid
    vendor = Vendor(name="NetJets", email="sales@netjets.com", domain="netjets.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    bid = Bid(
        row_id=row.id,
        item_title="NetJets Charter",
        item_url="https://netjets.com",
        price=None,
        source="vendor_directory",
        vendor_id=vendor.id,
        is_superseded=False,
    )
    session.add(bid)
    await session.commit()

    resp = await client.post(
        f"/outreach/rows/{row.id}/blast",
        json={
            "subject": "Inquiry: {{vendor_company}}",
            "body": "Hi {{vendor_name}}, looking for a jet charter.",
            "dry_run": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dry_run"
    assert data["would_send"] >= 1
    assert len(data["previews"]) >= 1
    # Check personalization worked
    preview = data["previews"][0]
    assert "NetJets" in preview["subject"]


# ---------------------------------------------------------------------------
# Scenario 11: SDUI Schema Hydration (vendor_directory)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_sdui_vendor_bid_gets_contact_vendor_action(session, auth_user_and_token):
    """Vendor directory bid produces contact_vendor intent in UI schema."""
    from services.sdui_builder import build_ui_schema

    user, _ = auth_user_and_token

    row = Row(
        title="Private jet charter",
        status="bids_arriving",
        user_id=user.id,
        is_service=True,
        service_category="private_aviation",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        item_title="NetJets",
        item_url="https://netjets.com",
        price=None,
        source="vendor_directory",
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    schema = build_ui_schema(None, row, [bid])
    assert schema["version"] == 1

    # Find ActionRow block
    action_rows = [b for b in schema["blocks"] if b.get("type") == "ActionRow"]
    assert len(action_rows) > 0
    actions = action_rows[0]["actions"]
    # Should have contact_vendor, NOT outbound_affiliate
    intents = [a["intent"] for a in actions]
    assert "contact_vendor" in intents
    assert "outbound_affiliate" not in intents


@pytest.mark.asyncio
async def test_e2e_sdui_amazon_bid_gets_affiliate_action(session, auth_user_and_token):
    """Amazon product bid produces outbound_affiliate intent in UI schema."""
    from services.sdui_builder import build_ui_schema

    user, _ = auth_user_and_token

    row = Row(title="Lawn mower", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        item_title="EGO Power+ Mower",
        item_url="https://www.amazon.com/dp/B09V3KXJPB",
        price=549.99,
        source="rainforest_amazon",
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    schema = build_ui_schema(None, row, [bid])
    action_rows = [b for b in schema["blocks"] if b.get("type") == "ActionRow"]
    assert len(action_rows) > 0
    actions = action_rows[0]["actions"]
    intents = [a["intent"] for a in actions]
    assert "outbound_affiliate" in intents
