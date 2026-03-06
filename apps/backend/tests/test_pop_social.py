"""Tests for Pop social layer routes (PRD-07: Likes & Comments).

Covers:
  - POST /pop/item/{row_id}/react — toggle like, optimistic
  - GET /pop/item/{row_id}/reactions — get reaction summary
  - POST /pop/item/{row_id}/comments — add comment
  - GET /pop/item/{row_id}/comments — list comments
  - DELETE /pop/item/{row_id}/comments/{id} — soft-delete own comment
  - Auth and membership checks
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, AuthSession, Row, Project, ProjectMember, hash_token, generate_session_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(name="social_user")
async def social_user_fixture(session: AsyncSession):
    user = User(email="social_user@example.com", is_admin=False, name="Alice")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = generate_session_token()
    auth_session = AuthSession(email=user.email, user_id=user.id, session_token_hash=hash_token(token))
    session.add(auth_session)
    await session.commit()
    return user, token


@pytest_asyncio.fixture(name="social_user2")
async def social_user2_fixture(session: AsyncSession):
    user = User(email="social_user2@example.com", is_admin=False, name="Bob")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = generate_session_token()
    auth_session = AuthSession(email=user.email, user_id=user.id, session_token_hash=hash_token(token))
    session.add(auth_session)
    await session.commit()
    return user, token


@pytest_asyncio.fixture(name="social_project")
async def social_project_fixture(session: AsyncSession, social_user):
    user, _ = social_user
    project = Project(title="Social Test List", user_id=user.id, status="active")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    # Add user as project member
    member = ProjectMember(project_id=project.id, user_id=user.id, role="owner")
    session.add(member)
    await session.commit()
    return project


@pytest_asyncio.fixture(name="social_row")
async def social_row_fixture(session: AsyncSession, social_user, social_project):
    user, _ = social_user
    row = Row(title="Organic Milk", status="sourcing", user_id=user.id, project_id=social_project.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_toggle_like_on(client: AsyncClient, social_user, social_row):
    """POST /pop/item/{id}/react likes an item."""
    _, token = social_user
    resp = await client.post(
        f"/pop/item/{social_row.id}/react",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["liked"] is True
    assert data["like_count"] == 1


@pytest.mark.asyncio
async def test_toggle_like_off(client: AsyncClient, social_user, social_row):
    """POST /pop/item/{id}/react twice toggles the like off."""
    _, token = social_user
    await client.post(f"/pop/item/{social_row.id}/react", headers={"Authorization": f"Bearer {token}"})
    resp = await client.post(f"/pop/item/{social_row.id}/react", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["liked"] is False
    assert data["like_count"] == 0


@pytest.mark.asyncio
async def test_get_reactions(client: AsyncClient, social_user, social_row):
    """GET /pop/item/{id}/reactions returns summary with user_liked."""
    _, token = social_user
    await client.post(f"/pop/item/{social_row.id}/react", headers={"Authorization": f"Bearer {token}"})
    resp = await client.get(f"/pop/item/{social_row.id}/reactions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["like_count"] == 1
    assert data["user_liked"] is True
    assert len(data["reactors"]) == 1
    assert data["reactors"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_react_401_without_auth(client: AsyncClient, social_row):
    """POST /pop/item/{id}/react returns 401 without auth."""
    resp = await client.post(f"/pop/item/{social_row.id}/react")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_react_404_nonexistent_row(client: AsyncClient, social_user):
    """POST /pop/item/99999/react returns 404 for nonexistent row."""
    _, token = social_user
    resp = await client.post("/pop/item/99999/react", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_react_403_non_member(
    client: AsyncClient, session: AsyncSession, social_user2, social_row,
):
    """POST /pop/item/{id}/react returns 403 for non-member."""
    _, token = social_user2
    resp = await client.post(f"/pop/item/{social_row.id}/react", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_comment(client: AsyncClient, social_user, social_row):
    """POST /pop/item/{id}/comments adds a comment."""
    _, token = social_user
    resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "Get the 2% kind!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Get the 2% kind!"
    assert data["user_name"] == "Alice"
    assert data["row_id"] == social_row.id


@pytest.mark.asyncio
async def test_get_comments(client: AsyncClient, social_user, social_row):
    """GET /pop/item/{id}/comments returns comment list."""
    _, token = social_user
    await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "First comment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "Second comment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        f"/pop/item/{social_row.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["comments"]) == 2


@pytest.mark.asyncio
async def test_add_comment_empty_text(client: AsyncClient, social_user, social_row):
    """POST /pop/item/{id}/comments with empty text returns 400."""
    _, token = social_user
    resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_comment_too_long(client: AsyncClient, social_user, social_row):
    """POST /pop/item/{id}/comments with 501+ chars returns 400."""
    _, token = social_user
    resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "x" * 501},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_comment(client: AsyncClient, social_user, social_row):
    """DELETE /pop/item/{id}/comments/{cid} soft-deletes own comment."""
    _, token = social_user
    add_resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "To be deleted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    cid = add_resp.json()["id"]
    del_resp = await client.delete(
        f"/pop/item/{social_row.id}/comments/{cid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify it's gone from the list
    list_resp = await client.get(
        f"/pop/item/{social_row.id}/comments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_comment_403_other_user(
    client: AsyncClient, session: AsyncSession, social_user, social_user2, social_project, social_row,
):
    """DELETE /pop/item/{id}/comments/{cid} returns 403 for other user."""
    _, token1 = social_user
    user2, token2 = social_user2
    # Add user2 as member so they can try
    member = ProjectMember(project_id=social_project.id, user_id=user2.id, role="member")
    session.add(member)
    await session.commit()

    add_resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "User1's comment"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    cid = add_resp.json()["id"]
    del_resp = await client.delete(
        f"/pop/item/{social_row.id}/comments/{cid}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert del_resp.status_code == 403


@pytest.mark.asyncio
async def test_comment_401_without_auth(client: AsyncClient, social_row):
    """POST /pop/item/{id}/comments returns 401 without auth."""
    resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_comment_403_non_member(client: AsyncClient, social_user2, social_row):
    """POST /pop/item/{id}/comments returns 403 for non-member."""
    _, token = social_user2
    resp = await client.post(
        f"/pop/item/{social_row.id}/comments",
        json={"text": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
