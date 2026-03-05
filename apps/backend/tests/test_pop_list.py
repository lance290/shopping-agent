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


# Join-list tests (section 6) extracted to test_pop_list_crud.py


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


# ---------------------------------------------------------------------------
# PRD-02: Grocery Taxonomy & Attribution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_item_taxonomy_fields(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """PATCH /pop/item/{id} accepts and persists taxonomy fields in choice_answers."""
    _, token = pop_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"department": "Dairy", "brand": "Tillamook", "quantity": "2", "size": "gallon"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["department"] == "Dairy"
    assert data["brand"] == "Tillamook"
    assert data["quantity"] == "2"
    assert data["size"] == "gallon"

    await session.refresh(pop_row)
    answers = pop_row.choice_answers or {}
    assert answers["department"] == "Dairy"
    assert answers["brand"] == "Tillamook"


@pytest.mark.asyncio
async def test_patch_item_title_and_taxonomy(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """PATCH /pop/item/{id} can update title and taxonomy in one request."""
    _, token = pop_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"title": "Organic Whole Milk", "department": "Dairy"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Organic Whole Milk"
    assert data["department"] == "Dairy"


@pytest.mark.asyncio
async def test_patch_item_returns_attribution(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """PATCH response includes origin_channel and origin_user_id."""
    user, token = pop_user
    pop_row.origin_channel = "sms"
    pop_row.origin_user_id = user.id
    session.add(pop_row)
    await session.commit()

    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"department": "Produce"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin_channel"] == "sms"
    assert data["origin_user_id"] == user.id


