"""Tests for Pop list, invite, item CRUD, and offer claim routes."""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid

# ---------------------------------------------------------------------------
# 2. GET /pop/list/{project_id}  (requires auth + membership)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_returns_items(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/list/{id} returns project + list items for an authenticated member."""
    user, token = pop_user
    # Ensure user is a project member
    from routes.pop_helpers import _ensure_project_member
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    resp = await client.get(
        f"/pop/list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert isinstance(data["items"], list)
    assert any(item["title"] == "Whole milk" for item in data["items"])


@pytest.mark.asyncio
async def test_get_list_401_without_auth(client: AsyncClient, pop_project: Project):
    """GET /pop/list/{id} returns 401 without auth."""
    resp = await client.get(f"/pop/list/{pop_project.id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_list_404_for_unknown_project(client: AsyncClient, pop_user):
    """GET /pop/list/999999 returns 404 for non-existent project."""
    _, token = pop_user
    resp = await client.get("/pop/list/999999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_list_excludes_canceled_rows(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
):
    """Canceled rows must NOT appear in the list view."""
    user, token = pop_user
    from routes.pop_helpers import _ensure_project_member
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    canceled = Row(
        title="Canceled item",
        status="canceled",
        user_id=user.id,
        project_id=pop_project.id,
    )
    session.add(canceled)
    await session.commit()

    resp = await client.get(
        f"/pop/list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert "Canceled item" not in titles


@pytest.mark.asyncio
async def test_get_list_swap_heuristic(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Bids whose titles diverge from the row title appear as swap suggestions."""
    from models import Bid
    from routes.pop_helpers import _ensure_project_member
    user, token = pop_user
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    # Near-exact match — NOT a swap
    matching_bid = Bid(
        row_id=pop_row.id,
        price=3.99,
        total_cost=3.99,
        item_title="Whole Milk Gallon",
        item_url="https://example.com/milk",
    )
    # Completely different product — IS a swap (explicitly flagged)
    swap_bid = Bid(
        row_id=pop_row.id,
        price=2.99,
        total_cost=2.99,
        item_title="Almond Breeze Oat Milk",
        item_url="https://example.com/oat",
        is_swap=True,
    )
    session.add_all([matching_bid, swap_bid])
    await session.commit()

    resp = await client.get(
        f"/pop/list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["deal_count"] >= 1
    # The oat milk bid should appear as a swap (low title overlap with "Whole milk")
    swap_titles = [s["title"] for s in item.get("swaps", [])]
    assert "Almond Breeze Oat Milk" in swap_titles


# ---------------------------------------------------------------------------
# 3. GET /pop/my-list  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_list_401_without_auth(client: AsyncClient):
    """GET /pop/my-list returns 401 when no token is provided."""
    resp = await client.get("/pop/my-list")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_my_list_returns_empty_when_no_project(
    client: AsyncClient,
    pop_user,
):
    """GET /pop/my-list returns empty list when user has no project yet."""
    _, token = pop_user
    resp = await client.get("/pop/my-list", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] is None
    assert data["items"] == []


@pytest.mark.asyncio
async def test_my_list_returns_active_project(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/my-list returns the user's Family Shopping List project."""
    _, token = pop_user
    resp = await client.get("/pop/my-list", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert any(i["title"] == "Whole milk" for i in data["items"])


# ---------------------------------------------------------------------------
# 4. POST /pop/list/{project_id}/invite  (requires auth, must own project)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_invite_401_without_auth(
    client: AsyncClient, pop_project: Project
):
    """Creating an invite without auth returns 401."""
    resp = await client.post(f"/pop/list/{pop_project.id}/invite")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_invite_returns_token_and_url(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
):
    """POST /pop/list/{id}/invite returns token + invite_url."""
    _, token = pop_user
    resp = await client.post(
        f"/pop/list/{pop_project.id}/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "invite_url" in data
    assert data["expires_days"] == 30
    assert len(data["token"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_create_invite_404_for_nonexistent_project(
    client: AsyncClient, pop_user
):
    """POST /pop/list/999999/invite returns 404 for non-existent project."""
    _, token = pop_user
    resp = await client.post(
        "/pop/list/999999/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. GET /pop/invite/{token}  (public)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_invite_returns_project_info(
    client: AsyncClient,
    pop_invite: ProjectInvite,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/invite/{token} returns project title + item count."""
    resp = await client.get(f"/pop/invite/{pop_invite.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert data["item_count"] == 1  # one sourcing row
    assert data["token"] == pop_invite.id


@pytest.mark.asyncio
async def test_resolve_invite_404_for_unknown_token(client: AsyncClient):
    """GET /pop/invite/bogus returns 404."""
    resp = await client.get("/pop/invite/does-not-exist-abc123")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_invite_410_when_expired(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
):
    """Regression: expired invite must return 410, not 200."""
    import uuid
    user, _ = pop_user
    expired = ProjectInvite(
        id=str(uuid.uuid4()),
        project_id=pop_project.id,
        invited_by=user.id,
        expires_at=datetime.utcnow() - timedelta(days=1),  # already expired
    )
    session.add(expired)
    await session.commit()

    resp = await client.get(f"/pop/invite/{expired.id}")
    assert resp.status_code == 410, "Expired invite must return 410 Gone"


# ---------------------------------------------------------------------------
# 6. POST /pop/join-list/{project_id}  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_join_list_401_without_auth(
    client: AsyncClient, pop_project: Project, pop_invite: ProjectInvite
):
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        json={"token": pop_invite.id},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_join_list_creates_member(
    client: AsyncClient,
    session: AsyncSession,
    other_user,
    pop_project: Project,
    pop_invite: ProjectInvite,
):
    """Authenticated user joins a shared list with valid invite token — ProjectMember record created."""
    user, token = other_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        json={"token": pop_invite.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["joined"] is True
    assert data["project_id"] == pop_project.id

    # Verify DB record
    from sqlmodel import select
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == pop_project.id,
        ProjectMember.user_id == user.id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()
    assert member is not None
    assert member.channel == "web"


@pytest.mark.asyncio
async def test_join_list_idempotent(
    client: AsyncClient,
    other_user,
    pop_project: Project,
    pop_invite: ProjectInvite,
):
    """Joining the same list twice with the same invite token — idempotent."""
    _, token = other_user
    headers = {"Authorization": f"Bearer {token}"}
    body = {"token": pop_invite.id}
    r1 = await client.post(f"/pop/join-list/{pop_project.id}", json=body, headers=headers)
    r2 = await client.post(f"/pop/join-list/{pop_project.id}", json=body, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_join_list_404_for_invalid_token(client: AsyncClient, pop_user, pop_project: Project):
    """Invalid invite token returns 404."""
    _, token = pop_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        json={"token": "nonexistent-token-abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_list_422_without_token(client: AsyncClient, pop_user, pop_project: Project):
    """POST /join-list without token in body returns 422 (validation error)."""
    _, token = pop_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. PATCH /pop/item/{row_id}  (requires auth, owner-only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_item_renames_row(
    client: AsyncClient,
    pop_user,
    pop_row: Row,
):
    """PATCH /pop/item/{id} renames the row title."""
    _, token = pop_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"title": "Organic whole milk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Organic whole milk"
    assert data["id"] == pop_row.id


@pytest.mark.asyncio
async def test_patch_item_401_without_auth(client: AsyncClient, pop_row: Row):
    resp = await client.patch(f"/pop/item/{pop_row.id}", json={"title": "X"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_patch_item_404_for_other_users_row(
    client: AsyncClient,
    other_user,
    pop_row: Row,
):
    """Regression: user cannot rename another user's row — must get 404."""
    _, token = other_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"title": "Hijacked title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, "Cross-user item rename must return 404"


@pytest.mark.asyncio
async def test_patch_item_404_for_nonexistent_row(
    client: AsyncClient, pop_user
):
    _, token = pop_user
    resp = await client.patch(
        "/pop/item/999999",
        json={"title": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. DELETE /pop/item/{row_id}  (requires auth, owner-only, soft-delete)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_item_soft_deletes_row(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """DELETE /pop/item/{id} sets status='canceled' (soft delete)."""
    _, token = pop_user
    resp = await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    await session.refresh(pop_row)
    assert pop_row.status == "canceled", "Row must be soft-deleted (status=canceled)"


@pytest.mark.asyncio
async def test_delete_item_401_without_auth(client: AsyncClient, pop_row: Row):
    resp = await client.delete(f"/pop/item/{pop_row.id}")
    assert resp.status_code == 401


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


