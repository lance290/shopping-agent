"""Tests for Pop list item CRUD, join, and offer claim routes.
Extracted from test_pop_list.py to keep files under 450 lines.
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid


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
    assert data["status"] == "joined"

    from sqlmodel import select
    result = await session.exec(
        select(ProjectMember).where(
            ProjectMember.project_id == pop_project.id,
            ProjectMember.user_id == user.id,
        )
    )
    member = result.first()
    assert member is not None


@pytest.mark.asyncio
async def test_join_list_invalid_token_403(
    client: AsyncClient,
    other_user,
    pop_project: Project,
):
    """Attempting to join with an invalid invite token returns 403."""
    _, token = other_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        json={"token": "bogus-token-abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_join_list_expired_invite_403(
    client: AsyncClient,
    session: AsyncSession,
    other_user,
    pop_project: Project,
    pop_invite: ProjectInvite,
):
    """Expired invites should return 403."""
    pop_invite.expires_at = datetime.utcnow() - timedelta(days=1)
    session.add(pop_invite)
    await session.commit()

    _, token = other_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        json={"token": pop_invite.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
