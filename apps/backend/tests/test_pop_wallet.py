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
async def test_receipt_scan_swap_earns_extra_credits(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Swap purchases earn 50 cents (vs 25 for regular match)."""
    _, token = pop_user
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


