"""Integration tests for project routes (CRUD + row unlinking)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project_requires_auth(client: AsyncClient):
    res = await client.post("/projects", json={"title": "Test"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_user_and_token):
    user, token = auth_user_and_token
    res = await client.post(
        "/projects",
        json={"title": "Birthday Party"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Birthday Party"
    assert data["user_id"] == user.id
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_user_and_token):
    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/projects", json={"title": "Proj A"}, headers=headers)
    await client.post("/projects", json={"title": "Proj B"}, headers=headers)

    res = await client.get("/projects", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    # Newest first
    assert data[0]["title"] == "Proj B"
    assert data[1]["title"] == "Proj A"


@pytest.mark.asyncio
async def test_list_projects_user_isolation(client: AsyncClient, session, auth_user_and_token):
    """Users only see their own projects."""
    user, token = auth_user_and_token
    from models import User, Project

    other_user = User(email="other@test.com", is_admin=False)
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    other_project = Project(title="Other's Project", user_id=other_user.id)
    session.add(other_project)
    await session.commit()

    # Create one project for our user
    await client.post(
        "/projects",
        json={"title": "My Project"},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.get(
        "/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Project"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_user_and_token):
    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post("/projects", json={"title": "To Delete"}, headers=headers)
    project_id = create_res.json()["id"]

    delete_res = await client.delete(f"/projects/{project_id}", headers=headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["status"] == "deleted"

    # Verify gone
    list_res = await client.get("/projects", headers=headers)
    assert len(list_res.json()) == 0


@pytest.mark.asyncio
async def test_delete_project_unlinks_rows(client: AsyncClient, session, auth_user_and_token):
    """Deleting a project should set project_id=None on its child rows."""
    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}
    from models import Row

    # Create project
    proj_res = await client.post("/projects", json={"title": "Temp Proj"}, headers=headers)
    project_id = proj_res.json()["id"]

    # Create a row under this project
    row = Row(title="Row in project", status="sourcing", user_id=user.id, project_id=project_id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Delete project
    await client.delete(f"/projects/{project_id}", headers=headers)

    # Verify row's project_id is now None
    await session.refresh(row)
    assert row.project_id is None


@pytest.mark.asyncio
async def test_delete_nonexistent_project(client: AsyncClient, auth_user_and_token):
    _, token = auth_user_and_token
    res = await client.delete(
        "/projects/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_project(client: AsyncClient, session, auth_user_and_token):
    """Cannot delete another user's project."""
    _, token = auth_user_and_token
    from models import User, Project

    other_user = User(email="someone@else.com", is_admin=False)
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    project = Project(title="Not Mine", user_id=other_user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    res = await client.delete(
        f"/projects/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
