"""Tests for Pop wallet and receipt scan routes."""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid

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
async def test_receipt_scan_no_items_returns_graceful_message(
    client: AsyncClient, pop_user
):
    """When OCR returns no items, scan returns status=no_items (not a crash)."""
    _, token = pop_user
    with patch("routes.pop_wallet._extract_receipt_items", new_callable=AsyncMock, return_value=[]):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA=="},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "no_items"
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
    mock_items = [{"name": "Whole milk", "price": 3.49, "is_swap": False}]
    with patch("routes.pop_wallet._extract_receipt_items", new_callable=AsyncMock, return_value=mock_items):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scanned"
    assert data["credits_earned_cents"] >= 25
    assert data["total_items"] == 1


@pytest.mark.asyncio
async def test_receipt_scan_triggers_referral_revenue_share(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """
    When a referred user earns swap credits, 30% of their earnings
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

    # 3. Simulate a receipt scan that earns 50 cents (swap)
    mock_items = [{"name": "Whole milk", "price": 3.49, "is_swap": True}]
    with patch("routes.pop_wallet._extract_receipt_items", new_callable=AsyncMock, return_value=mock_items):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["credits_earned_cents"] == 50
    
    # 4. Check referrer's wallet balance
    # Base 1000 + (50 * 0.3) = 1000 + 15 = 1015
    await session.refresh(referrer)
    assert referrer.wallet_balance_cents == 1015


