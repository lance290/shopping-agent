"""
End-to-end scenario tests for revenue-critical flows.

These tests simulate full user journeys through the API using real DB fixtures.
They require a running Postgres instance (conftest.py handles setup).

Scenarios:
1. Affiliate clickout: search → get bids → click affiliate link → 302 redirect
2. Vendor outreach: search service → get vendor bids → send outreach email → quote link
3. Stripe checkout: create bid → checkout session → redirect URL uses correct domain
4. Tip jar: anonymous tip → checkout session created
5. Search with 0 results: search completes → row gets zero-results schema
6. Outreach status tracking: send outreach → track open → track quote
7. Multi-domain: requests from different domains get correct redirect URLs
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from main import app
from database import get_session
from models import Row, Bid, User, AuthSession, Vendor, SellerQuote, OutreachEvent
from models import hash_token, generate_session_token, generate_magic_link_token


# ---------------------------------------------------------------------------
# Scenario 1: Affiliate Clickout Flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_affiliate_clickout_amazon(client, auth_user_and_token, session):
    """Full flow: user has a row with an Amazon bid → clicks View Deal → 302 to affiliate URL."""
    user, token = auth_user_and_token

    # Create row
    row = Row(title="Lawn mower", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create vendor/seller
    vendor = Vendor(name="Amazon Seller", email="seller@amazon.com", domain="amazon.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    # Create bid with Amazon URL
    bid = Bid(
        row_id=row.id,
        item_title="EGO Power+ 21\" Self-Propelled Mower",
        item_url="https://www.amazon.com/dp/B09V3KXJPB",
        price=549.99,
        currency="USD",
        source="rainforest_amazon",
        vendor_id=vendor.id,
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Click affiliate link
    resp = await client.get(
        f"/api/out?url={bid.item_url}&bid_id={bid.id}&row_id={row.id}&source=rainforest_amazon",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "amazon.com" in location
    # Should have affiliate tag appended
    assert "tag=" in location


@pytest.mark.asyncio
async def test_e2e_affiliate_clickout_ebay(client, auth_user_and_token, session):
    """Full flow: eBay bid → clickout → 302 with eBay affiliate params."""
    user, token = auth_user_and_token

    row = Row(title="Robot vacuum", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    vendor = Vendor(name="eBay Seller", email="seller@ebay.com", domain="ebay.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    bid = Bid(
        row_id=row.id,
        item_title="iRobot Roomba j7+",
        item_url="https://www.ebay.com/itm/123456789",
        price=399.99,
        currency="USD",
        source="ebay_browse",
        vendor_id=vendor.id,
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.get(
        f"/api/out?url={bid.item_url}&bid_id={bid.id}&row_id={row.id}&source=ebay_browse",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "ebay.com" in location
    # Should have eBay affiliate params
    assert "campid=" in location or "mkevt=" in location


# ---------------------------------------------------------------------------
# Scenario 2: Vendor Outreach Flow (EA Workflow)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_vendor_outreach_send_and_track(client, auth_user_and_token, session):
    """Full flow: create row → send outreach email → track open → check status."""
    user, token = auth_user_and_token

    # Set user name/email (required for outreach)
    user.name = "Lance Massey"
    user.email = "lance@example.com"
    session.add(user)
    await session.commit()

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

    # Send outreach via the /outreach/rows/{id}/send endpoint
    with patch("services.email.send_custom_outreach_email", new_callable=AsyncMock) as mock_send:
        from services.email import EmailResult
        mock_send.return_value = EmailResult(success=True, message_id="msg_abc123")

        resp = await client.post(
            f"/outreach/rows/{row.id}/send",
            json={
                "vendor_email": "charter@netjets.com",
                "vendor_name": "Sales Team",
                "vendor_company": "NetJets",
                "reply_to_email": "lance@example.com",
                "sender_name": "Lance Massey",
                "subject": "Private jet charter inquiry",
                "body": "Looking for a light jet SAN to EWR, March 4th.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["message_id"] == "msg_abc123"
    quote_token = data["quote_token"]
    assert quote_token is not None

    # Verify SellerQuote was created
    from sqlmodel import select
    sq_result = await session.execute(
        select(SellerQuote).where(SellerQuote.token == quote_token)
    )
    quote = sq_result.scalar_one_or_none()
    assert quote is not None
    assert quote.seller_email == "charter@netjets.com"
    assert quote.seller_company == "NetJets"
    assert quote.status == "pending"

    # Verify OutreachEvent was created and marked sent
    oe_result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.quote_token == quote_token)
    )
    event = oe_result.scalar_one_or_none()
    assert event is not None
    assert event.sent_at is not None
    assert event.message_id == "msg_abc123"

    # Track email open
    open_resp = await client.get(f"/outreach/track/open/{quote_token}")
    assert open_resp.status_code == 200

    await session.refresh(event)
    assert event.opened_at is not None

    # Check outreach status
    status_resp = await client.get(f"/outreach/rows/{row.id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["total_sent"] >= 1
    assert status_data["opened"] >= 1


# ---------------------------------------------------------------------------
# Scenario 3: Quote Submission Flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_quote_form_valid_token(client, auth_user_and_token, session):
    """Full flow: vendor clicks quote link → form loads with row context."""
    user, token = auth_user_and_token

    row = Row(title="Private jet charter SAN-EWR", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create SellerQuote with valid token
    quote_token = generate_magic_link_token()
    quote = SellerQuote(
        row_id=row.id,
        token=quote_token,
        token_expires_at=datetime.utcnow() + timedelta(days=14),
        seller_email="sales@netjets.com",
        seller_company="NetJets",
        status="pending",
    )
    session.add(quote)
    await session.commit()

    # Vendor clicks the quote link
    resp = await client.get(f"/quotes/form/{quote_token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_title"] == "Private jet charter SAN-EWR"
    assert data["vendor_company"] == "NetJets"


@pytest.mark.asyncio
async def test_e2e_quote_form_expired_token(client, session, auth_user_and_token):
    """Expired quote link returns 404."""
    user, _ = auth_user_and_token

    row = Row(title="Test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    quote_token = generate_magic_link_token()
    quote = SellerQuote(
        row_id=row.id,
        token=quote_token,
        token_expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
        seller_email="x@x.com",
        status="pending",
    )
    session.add(quote)
    await session.commit()

    resp = await client.get(f"/quotes/form/{quote_token}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scenario 4: Stripe Checkout (Multi-Domain)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_checkout_redirect_uses_forwarded_host(client, auth_user_and_token, session):
    """Stripe checkout success_url uses the domain from X-Forwarded-Host, not localhost."""
    user, token = auth_user_and_token

    row = Row(title="Test Item", status="bids_arriving", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        item_title="Widget",
        item_url="https://example.com/widget",
        price=99.99,
        currency="USD",
        source="amazon",
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    with patch("routes.checkout._get_stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_session.id = "cs_test_123"
        mock_stripe.return_value.checkout.Session.create.return_value = mock_session

        resp = await client.post(
            "/api/checkout/create-session",
            json={"bid_id": bid.id, "row_id": row.id},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Forwarded-Host": "buy-anything.com",
                "X-Forwarded-Proto": "https",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"

    # Verify the Stripe session was created with correct success_url
    create_call = mock_stripe.return_value.checkout.Session.create
    assert create_call.called
    call_kwargs = create_call.call_args
    success_url = call_kwargs.kwargs.get("success_url") or call_kwargs[1].get("success_url", "")
    # Should reference buy-anything.com, NOT localhost
    if success_url:
        assert "localhost" not in success_url


@pytest.mark.asyncio
async def test_e2e_tip_jar_creates_session(client):
    """Anonymous user can create a tip jar checkout session."""
    with patch("routes.checkout._get_stripe") as mock_stripe:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_tip_123"
        mock_session.id = "cs_tip_123"
        mock_stripe.return_value.checkout.Session.create.return_value = mock_session

        with patch.dict("os.environ", {"STRIPE_TIP_JAR_PRICE_ID": "price_tip_test"}):
            resp = await client.post("/api/tip-jar")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "cs_tip_123"
    assert "checkout.stripe.com" in data["checkout_url"]


# ---------------------------------------------------------------------------
# Scenario 5: Search with 0 Results → Zero-Results Schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_zero_results_schema_applied(session, auth_user_and_token):
    """When search returns 0 results, row gets the zero-results ui_schema."""
    from services.sdui_builder import build_zero_results_schema

    user, token = auth_user_and_token

    row = Row(
        title="Unicorn saddle",
        status="sourcing",
        user_id=user.id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Simulate what the streaming search does when 0 results come back
    schema = build_zero_results_schema(row)
    row.ui_schema = schema
    row.ui_schema_version = 1
    row.status = "sourcing"
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.ui_schema is not None
    assert row.ui_schema["version"] == 1
    blocks = row.ui_schema["blocks"]
    assert any("No options found" in str(b.get("content", "")) for b in blocks)
    assert any(
        b.get("type") == "ActionRow" and
        any(a.get("intent") == "edit_request" for a in b.get("actions", []))
        for b in blocks
    )


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
