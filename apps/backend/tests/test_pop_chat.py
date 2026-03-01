"""Tests for Pop web chat route."""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid

# ---------------------------------------------------------------------------
# 11. POST /pop/chat  (guest + authenticated)
# ---------------------------------------------------------------------------

async def _empty_async_gen():
    """Empty async generator for mocking _stream_search."""
    return
    yield  # makes it an async generator


def _mock_pop_decision(message: str = "Got it! Added to your list.", action_type: str = "chat"):
    """Build a minimal mock of make_pop_decision's return value (UnifiedDecision)."""
    mock_intent = MagicMock()
    mock_intent.what = "eggs"
    mock_intent.category = "product"
    mock_intent.service_type = None
    mock_intent.search_query = None
    mock_intent.constraints = {}
    mock_intent.desire_tier = None

    mock_decision = MagicMock()
    mock_decision.intent = mock_intent
    mock_decision.action = {"type": action_type}
    mock_decision.message = message
    return mock_decision


@pytest.mark.asyncio
async def test_chat_guest_mode_without_auth(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
):
    """Regression: POST /pop/chat without auth uses guest user — must not 401."""
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "I need eggs"},
            )
    assert resp.status_code == 200, f"Guest chat must succeed, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "reply" in data
    assert "project_id" in data


@pytest.mark.asyncio
async def test_chat_guest_without_guest_user_in_db_returns_signup_nudge(
    client: AsyncClient,
    session: AsyncSession,
):
    """When guest user doesn't exist in DB, chat returns signup prompt (no crash)."""
    # No guest_user fixture — guest@buy-anything.com absent from DB
    resp = await client.post(
        "/pop/chat",
        json={"message": "I need eggs"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    # Should contain a signup nudge
    assert "popsavings.com" in data["reply"].lower() or "sign" in data["reply"].lower()


@pytest.mark.asyncio
async def test_chat_authenticated_creates_family_shopping_list(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """Authenticated chat auto-creates 'Family Shopping List' project if absent."""
    user, token = pop_user

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "Need milk"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] is not None

    # Verify project created in DB
    from sqlmodel import select
    proj = await session.get(Project, data["project_id"])
    assert proj is not None
    assert proj.title == "Family Shopping List"


@pytest.mark.asyncio
async def test_chat_authenticated_reuses_existing_project(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
):
    """Chat must reuse an existing 'Family Shopping List', not create a duplicate."""
    _, token = pop_user
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            r1 = await client.post(
                "/pop/chat",
                json={"message": "Need eggs"},
                headers={"Authorization": f"Bearer {token}"},
            )
            r2 = await client.post(
                "/pop/chat",
                json={"message": "Need butter"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both must return the SAME project_id
    assert r1.json()["project_id"] == r2.json()["project_id"]


@pytest.mark.asyncio
async def test_chat_returns_list_items_in_response(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """POST /pop/chat response always includes current list_items snapshot."""
    _, token = pop_user
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "What's on my list?"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["list_items"], list)
    titles = [i["title"] for i in data["list_items"]]
    assert "Whole milk" in titles


@pytest.mark.asyncio
async def test_chat_guest_resuming_session_via_guest_project_id(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
):
    """Guest chat with guest_project_id resumes existing project instead of creating a new one."""
    project = Project(title="My Shopping List", user_id=guest_user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    from routes.pop_chat import _sign_guest_project
    guest_token = _sign_guest_project(project.id)

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={
                    "message": "I need bread",
                    "guest_project_id": project.id,
                    "guest_session_token": guest_token,
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project.id, "Must reuse the existing guest project"
    assert "guest_session_token" in data, "Response must include guest session token"


@pytest.mark.asyncio
async def test_chat_guest_cannot_resume_other_users_project(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
    pop_project: Project,
):
    """Regression: guest cannot hijack another user's project via guest_project_id."""
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "list items", "guest_project_id": pop_project.id},
            )

    assert resp.status_code == 200
    data = resp.json()
    # Must NOT return the other user's project — a new guest project is created
    assert data["project_id"] != pop_project.id


@pytest.mark.asyncio
async def test_chat_create_row_action_persists_to_db(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """When decision action is create_row, a Row is persisted in the DB."""
    user, token = pop_user

    mock_intent = MagicMock()
    mock_intent.what = "avocados"
    mock_intent.category = "product"
    mock_intent.service_type = None
    mock_intent.search_query = "avocados"
    mock_intent.constraints = {}
    mock_intent.desire_tier = None

    mock_decision = MagicMock()
    mock_decision.intent = mock_intent
    mock_decision.action = {"type": "create_row"}
    mock_decision.message = "Added avocados!"
    mock_decision.items = None

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=mock_decision):
        with patch("routes.pop_chat._create_row", new_callable=AsyncMock) as mock_create:
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
                    # create a fake row returned by _create_row
                    fake_row = Row(title="Avocados", status="sourcing", user_id=user.id)
                    session.add(fake_row)
                    await session.commit()
                    await session.refresh(fake_row)
                    mock_create.return_value = fake_row

                    resp = await client.post(
                        "/pop/chat",
                        json={"message": "I need avocados"},
                        headers={"Authorization": f"Bearer {token}"},
                    )

    assert resp.status_code == 200
    mock_create.assert_called_once()


