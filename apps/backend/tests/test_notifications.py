"""Integration tests for notification routes."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_notifications_requires_auth(client: AsyncClient):
    res = await client.get("/notifications")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient, auth_user_and_token):
    user, token = auth_user_and_token
    res = await client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_create_and_list_notifications(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    await create_notification(
        session, user_id=user.id, type="test",
        title="Hello", body="Test body",
    )
    await session.commit()

    res = await client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Hello"
    assert data[0]["body"] == "Test body"
    assert data[0]["read"] is False


@pytest.mark.asyncio
async def test_unread_count(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    await create_notification(session, user_id=user.id, type="a", title="N1")
    await create_notification(session, user_id=user.id, type="b", title="N2")
    await session.commit()

    res = await client.get(
        "/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["unread"] == 2


@pytest.mark.asyncio
async def test_mark_read(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    notif = await create_notification(
        session, user_id=user.id, type="test", title="Read me",
    )
    await session.commit()
    await session.refresh(notif)

    res = await client.post(
        f"/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Verify count dropped
    count_res = await client.get(
        "/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert count_res.json()["unread"] == 0


@pytest.mark.asyncio
async def test_mark_read_wrong_user(client: AsyncClient, session, auth_user_and_token):
    """Cannot mark another user's notification as read."""
    user, token = auth_user_and_token
    from models import User
    from routes.notifications import create_notification

    other_user = User(email="other@example.com", is_admin=False)
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    notif = await create_notification(
        session, user_id=other_user.id, type="test", title="Not yours",
    )
    await session.commit()
    await session.refresh(notif)

    res = await client.post(
        f"/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    await create_notification(session, user_id=user.id, type="a", title="N1")
    await create_notification(session, user_id=user.id, type="b", title="N2")
    await create_notification(session, user_id=user.id, type="c", title="N3")
    await session.commit()

    res = await client.post(
        "/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200

    count_res = await client.get(
        "/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert count_res.json()["unread"] == 0


@pytest.mark.asyncio
async def test_list_unread_only(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    n1 = await create_notification(session, user_id=user.id, type="a", title="Unread")
    n2 = await create_notification(session, user_id=user.id, type="b", title="Will be read")
    await session.commit()
    await session.refresh(n2)

    # Mark n2 as read
    await client.post(
        f"/notifications/{n2.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    # List unread only
    res = await client.get(
        "/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Unread"


@pytest.mark.asyncio
async def test_notification_with_action_url(client: AsyncClient, session, auth_user_and_token):
    user, token = auth_user_and_token
    from routes.notifications import create_notification

    await create_notification(
        session, user_id=user.id, type="quote",
        title="New quote", action_url="/row/5",
        resource_type="quote", resource_id=42,
    )
    await session.commit()

    res = await client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = res.json()
    assert data[0]["action_url"] == "/row/5"
    assert data[0]["resource_type"] == "quote"
    assert data[0]["resource_id"] == 42
