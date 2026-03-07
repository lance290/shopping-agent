"""Tests for Pop wallet and receipt scan routes."""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid
from services.veryfi import VeryfiReceiptResult, VeryfiError


def _make_veryfi_result(items=None, vendor="Kroger", total=10.99, date="2026-03-07", fraud_score=0.0, fraud_types=None):
    """Build a mock VeryfiReceiptResult from minimal inputs."""
    raw = {
        "id": 12345,
        "vendor": {"name": vendor, "address": "123 Main St"},
        "total": total,
        "subtotal": total - 0.75,
        "tax": 0.75,
        "date": date,
        "currency_code": "USD",
        "line_items": items or [],
        "is_duplicate": False,
        "meta": {"fraud": {"score": fraud_score, "types": fraud_types or []}},
    }
    return VeryfiReceiptResult(raw)

# ---------------------------------------------------------------------------
# 9. GET /pop/wallet  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wallet_401_without_auth(client: AsyncClient):
    resp = await client.get("/pop/wallet")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wallet_returns_zero_balance_for_new_user(
    client: AsyncClient, pop_user
):
    """New user's wallet starts at 0 cents with no transactions."""
    _, token = pop_user
    resp = await client.get(
        "/pop/wallet",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance_cents"] == 0
    assert data["transactions"] == []


# ---------------------------------------------------------------------------
# 10. POST /pop/receipt/scan  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_receipt_scan_401_without_auth(client: AsyncClient):
    resp = await client.post(
        "/pop/receipt/scan",
        json={"image_base64": "dGVzdA=="},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_receipt_scan_veryfi_error_returns_friendly_message(
    client: AsyncClient, pop_user
):
    """When Veryfi fails, scan returns status=error with a friendly message (no fallback)."""
    _, token = pop_user
    with patch("routes.pop_wallet.process_receipt_base64", new_callable=AsyncMock, side_effect=VeryfiError("API down")):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA=="},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["credits_earned_cents"] == 0


@pytest.mark.asyncio
async def test_receipt_scan_fraud_detected_returns_rejected(
    client: AsyncClient, pop_user
):
    """When Veryfi detects fraud, scan returns status=rejected."""
    _, token = pop_user
    veryfi_result = _make_veryfi_result(fraud_score=0.9, fraud_types=["tampered"])
    with patch("routes.pop_wallet.process_receipt_base64", new_callable=AsyncMock, return_value=veryfi_result):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA=="},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["credits_earned_cents"] == 0


@pytest.mark.asyncio
async def test_receipt_scan_matches_list_items_and_earns_credits(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Receipt items that match list items earn 25 cents each."""
    _, token = pop_user
    veryfi_result = _make_veryfi_result(
        items=[{"description": "Whole milk", "total": 3.49, "quantity": 1, "price": 3.49, "sku": None, "upc": None}],
    )
    with patch("routes.pop_wallet.process_receipt_base64", new_callable=AsyncMock, return_value=veryfi_result):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["credits_earned_cents"] >= 25
    assert data["total_items"] == 1
    assert data["store_name"] == "Kroger"


@pytest.mark.asyncio
async def test_receipt_scan_applies_campaign_rebate_and_decrements_budget(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    user, token = pop_user

    from models import Vendor
    from models.coupons import Campaign

    vendor = Vendor(name="Hippeas", email="brand@example.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    campaign = Campaign(
        vendor_id=vendor.id,
        name="Hippeas Milk Conquest",
        swap_product_name="Organic whole milk",
        budget_total_cents=500,
        budget_remaining_cents=500,
        payout_per_swap_cents=50,
        target_categories="milk",
        target_competitors="whole milk",
        status="active",
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)

    veryfi_result = _make_veryfi_result(
        items=[{"description": "Organic whole milk", "total": 3.49, "quantity": 1, "price": 3.49, "sku": None, "upc": None}],
    )

    with patch("routes.pop_wallet.process_receipt_base64", new_callable=AsyncMock, return_value=veryfi_result):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["credits_earned_cents"] == 75

    await session.refresh(campaign)
    assert campaign.budget_remaining_cents == 450

    await session.refresh(user)
    assert user.wallet_balance_cents == 75


@pytest.mark.asyncio
async def test_receipt_scan_triggers_referral_revenue_share(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """
    When a referred user earns credits, 30% of their earnings
    should be credited to their referrer's wallet.
    """
    user, token = pop_user

    # 1. Create a referrer user
    from models import User
    from models.pop import Referral
    referrer = User(email="referrer@example.com", is_admin=False, ref_code="TESTREF1", wallet_balance_cents=1000)
    session.add(referrer)
    await session.commit()
    await session.refresh(referrer)

    # 2. Link them via a referral
    referral = Referral(
        referrer_user_id=referrer.id,
        referred_user_id=user.id,
        ref_code="TESTREF1",
        status="activated",
    )
    session.add(referral)
    await session.commit()

    # 3. Simulate a receipt scan that earns 25 cents (matched item)
    veryfi_result = _make_veryfi_result(
        items=[{"description": "Whole milk", "total": 3.49, "quantity": 1, "price": 3.49, "sku": None, "upc": None}],
    )
    with patch("routes.pop_wallet.process_receipt_base64", new_callable=AsyncMock, return_value=veryfi_result):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["credits_earned_cents"] == 25

    # 4. Check referrer's wallet balance
    # Base 1000 + (25 * 0.3) = 1000 + 7 = 1007
    await session.refresh(referrer)
    assert referrer.wallet_balance_cents == 1007


