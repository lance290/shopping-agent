"""Extracted Pop list offer/claim tests from test_pop_list.py."""
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Row, Bid, Project, User, ProjectMember, AuthSession
from routes.pop_helpers import _build_item_with_deals


@pytest.mark.asyncio
async def test_delete_item_404_for_other_users_row(
    client: AsyncClient,
    other_user,
    pop_row: Row,
):
    """Regression: user cannot delete another user's row — must get 404."""
    _, token = other_user
    resp = await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, "Cross-user item delete must return 404"


# ---------------------------------------------------------------------------
# Offer claim / unclaim (PRD 3 — swap discovery and claiming)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_offer_marks_bid_selected(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """POST /pop/offer/{id}/claim marks bid as selected and returns claimed=True."""
    from models import Bid
    _, token = pop_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk", is_swap=True)
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.post(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["claimed"] is True
    assert data["bid_id"] == bid.id
    await session.refresh(bid)
    assert bid.is_selected is True


@pytest.mark.asyncio
async def test_claim_provider_swap_marks_swap_selected(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    from models.coupons import PopSwap

    user, token = pop_user
    swap = PopSwap(
        category="milk",
        target_product="Whole milk",
        swap_product_name="Oat Milk",
        offer_type="coupon",
        savings_cents=150,
        provider="manual",
        is_active=True,
    )
    session.add(swap)
    await session.commit()
    await session.refresh(swap)

    synthetic_id = swap.id + 1000000
    resp = await client.post(
        f"/pop/offer/{synthetic_id}/claim",
        json={"row_id": pop_row.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["claimed"] is True
    assert resp.json()["bid_id"] == synthetic_id

    item = await _build_item_with_deals(session, pop_row, user.id)
    selected_swaps = [swap for swap in item["swaps"] if swap.get("is_selected")]
    assert any(swap["id"] == synthetic_id for swap in selected_swaps)


@pytest.mark.asyncio
async def test_claim_clears_prior_selection(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """Claiming a new offer clears any previously selected bid on the same row."""
    from models import Bid
    _, token = pop_user
    bid_a = Bid(row_id=pop_row.id, price=3.00, total_cost=3.00, item_title="Brand A", is_selected=True)
    bid_b = Bid(row_id=pop_row.id, price=2.50, total_cost=2.50, item_title="Brand B")
    session.add_all([bid_a, bid_b])
    await session.commit()
    await session.refresh(bid_a)
    await session.refresh(bid_b)

    resp = await client.post(
        f"/pop/offer/{bid_b.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    await session.refresh(bid_a)
    await session.refresh(bid_b)
    assert bid_a.is_selected is False, "Prior claim must be cleared"
    assert bid_b.is_selected is True


@pytest.mark.asyncio
async def test_unclaim_offer(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """DELETE /pop/offer/{id}/claim removes the claim (is_selected=False)."""
    from models import Bid
    _, token = pop_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk", is_selected=True)
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.delete(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["claimed"] is False
    await session.refresh(bid)
    assert bid.is_selected is False


@pytest.mark.asyncio
async def test_claim_offer_401_without_auth(client: AsyncClient, pop_row: Row):
    """Unauthenticated claim attempt returns 401."""
    resp = await client.post(f"/pop/offer/999/claim")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_claim_offer_404_cross_user(
    client: AsyncClient,
    session: AsyncSession,
    other_user,
    pop_row: Row,
):
    """User cannot claim a bid on another user's row — 404."""
    from models import Bid
    _, token = other_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk")
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.post(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deleted_item_excluded_from_list(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """After soft-delete, the item should not appear in GET /pop/list."""
    user, token = pop_user
    from routes.pop_helpers import _ensure_project_member
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        f"/pop/list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    titles = [i["title"] for i in resp.json()["items"]]
    assert "Whole milk" not in titles


@pytest.mark.asyncio
async def test_build_item_with_deals_prefers_selected_then_quantum_blended_score(
    session: AsyncSession,
    pop_row: Row,
):
    selected_bid = Bid(
        row_id=pop_row.id,
        price=4.99,
        total_cost=4.99,
        item_title="Selected Pick",
        source="kroger",
        is_selected=True,
        combined_score=0.10,
        provenance={"blended_score": 0.05},
    )
    top_quantum_bid = Bid(
        row_id=pop_row.id,
        price=3.99,
        total_cost=3.99,
        item_title="Quantum Winner",
        source="rainforest_amazon",
        combined_score=0.40,
        provenance={"blended_score": 0.91},
    )
    lower_quantum_bid = Bid(
        row_id=pop_row.id,
        price=2.99,
        total_cost=2.99,
        item_title="Lower Quantum",
        source="ebay_browse",
        combined_score=0.95,
        provenance={"blended_score": 0.33},
    )
    session.add_all([selected_bid, top_quantum_bid, lower_quantum_bid])
    await session.commit()

    item = await _build_item_with_deals(session, pop_row)

    assert [deal["title"] for deal in item["deals"][:3]] == [
        "Selected Pick",
        "Quantum Winner",
        "Lower Quantum",
    ]


