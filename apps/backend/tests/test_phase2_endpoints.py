"""
Tests for Phase 2 new endpoints:
- Merchant registration
- Contract creation (DocuSign scaffold)
- Outreach unsubscribe
- PurchaseEvent model
"""
import pytest
import json
from datetime import datetime

from models import Merchant, Contract, PurchaseEvent


# ─── Merchant Registration ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_merchant_register_success(client):
    """Test successful merchant registration."""
    response = await client.post(
        "/merchants/register",
        json={
            "business_name": "Test Merchant Co",
            "contact_name": "Jane Doe",
            "email": f"test-merchant-{datetime.utcnow().timestamp()}@example.com",
            "phone": "+1-555-0100",
            "website": "https://testmerchant.com",
            "categories": ["electronics", "automotive"],
            "service_areas": ["US-CA", "US-NY"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "registered"
    assert "merchant_id" in data


@pytest.mark.asyncio
async def test_merchant_register_duplicate_email(client):
    """Test duplicate email registration is rejected."""
    unique_email = f"dup-{datetime.utcnow().timestamp()}@example.com"

    await client.post(
        "/merchants/register",
        json={
            "business_name": "First Co",
            "contact_name": "Alice",
            "email": unique_email,
            "categories": ["electronics"],
        },
    )

    response = await client.post(
        "/merchants/register",
        json={
            "business_name": "Second Co",
            "contact_name": "Bob",
            "email": unique_email,
            "categories": ["automotive"],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_merchant_search_empty(client):
    """Test merchant search returns empty when no verified merchants."""
    response = await client.get(
        "/merchants/search",
        params={"category": "nonexistent_category"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


# ─── Contract Creation (DocuSign Scaffold) ──────────────────────────

@pytest.mark.asyncio
async def test_contract_create_requires_auth(client):
    """Test contract creation requires authentication."""
    response = await client.post(
        "/contracts",
        json={
            "seller_email": "seller@example.com",
            "deal_value": 1000.00,
        },
    )
    assert response.status_code == 401


# ─── Outreach Unsubscribe ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_outreach_unsubscribe_unknown_token(client):
    """Test unsubscribe with unknown token returns not_found."""
    response = await client.get("/outreach/unsubscribe/nonexistent-token")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_found"


# ─── PurchaseEvent Model ───────────────────────────────────────────

def test_purchase_event_model():
    """Test PurchaseEvent model instantiation."""
    event = PurchaseEvent(
        user_id=1,
        bid_id=10,
        row_id=5,
        amount=99.99,
        currency="USD",
        payment_method="affiliate",
        status="completed",
    )
    assert event.amount == 99.99
    assert event.payment_method == "affiliate"
    assert event.status == "completed"


def test_purchase_event_stripe_fields():
    """Test PurchaseEvent with Stripe checkout fields."""
    event = PurchaseEvent(
        user_id=1,
        amount=249.00,
        payment_method="stripe_checkout",
        stripe_session_id="cs_test_123",
        stripe_payment_intent_id="pi_test_456",
    )
    assert event.stripe_session_id == "cs_test_123"
    assert event.stripe_payment_intent_id == "pi_test_456"


# ─── Merchant Model ────────────────────────────────────────────────

def test_merchant_model():
    """Test Merchant model instantiation."""
    merchant = Merchant(
        business_name="Test Corp",
        contact_name="John",
        email="john@test.com",
        categories=json.dumps(["electronics"]),
        service_areas=json.dumps(["nationwide"]),
        status="pending",
    )
    assert merchant.business_name == "Test Corp"
    assert merchant.status == "pending"
    cats = json.loads(merchant.categories)
    assert "electronics" in cats


# ─── Contract Model ────────────────────────────────────────────────

def test_contract_model():
    """Test Contract model instantiation."""
    contract = Contract(
        buyer_user_id=1,
        buyer_email="buyer@test.com",
        seller_email="seller@test.com",
        seller_company="Seller Corp",
        deal_value=5000.00,
        status="draft",
    )
    assert contract.status == "draft"
    assert contract.deal_value == 5000.00
    assert contract.docusign_envelope_id is None
