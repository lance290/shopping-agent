"""Tests for anonymous access to /projects endpoints.

Covers:
- GET /projects returns empty list for anonymous users (not 401)
- POST /projects creates project under guest user
- Authenticated users still get their own projects
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from models import User, Project


GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    user = User(email=GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_projects_anonymous_returns_200(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Anonymous GET /projects should return 200 with empty list, not 401."""
    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_projects_anonymous_returns_guest_projects(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """If guest user has projects, anonymous GET should return them."""
    project = Project(title="Guest Project", user_id=guest_user.id)
    session.add(project)
    await session.commit()

    response = await client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Guest Project"


@pytest.mark.asyncio
async def test_get_projects_anonymous_does_not_see_other_users_projects(
    client: AsyncClient, session: AsyncSession, guest_user: User, auth_user_and_token
):
    """Anonymous user should NOT see projects owned by other users."""
    user, _ = auth_user_and_token

    other_project = Project(title="Private Project", user_id=user.id)
    session.add(other_project)
    await session.commit()

    response = await client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    # Should not contain the other user's project
    titles = [p["title"] for p in data]
    assert "Private Project" not in titles


@pytest.mark.asyncio
async def test_post_projects_anonymous_creates_under_guest(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Anonymous POST /projects should create project under guest user."""
    response = await client.post(
        "/projects",
        json={"title": "Anon Project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Anon Project"
    assert data["user_id"] == guest_user.id


@pytest.mark.asyncio
async def test_get_projects_authenticated_returns_own(
    client: AsyncClient, session: AsyncSession, auth_user_and_token
):
    """Authenticated GET /projects should return only the user's projects."""
    user, token = auth_user_and_token

    project = Project(title="My Project", user_id=user.id)
    session.add(project)
    await session.commit()

    response = await client.get(
        "/projects",
        headers={"authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Project"


@pytest.mark.asyncio
async def test_get_projects_anonymous_auto_creates_guest_user(
    client: AsyncClient, session: AsyncSession
):
    """If no guest user exists, GET /projects should auto-create one and return 200."""
    # No guest user in DB
    result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
    assert result.first() is None

    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []

    # Guest user should now exist
    result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
    guest = result.first()
    assert guest is not None
    assert guest.email == GUEST_EMAIL
