import pytest
from httpx import AsyncClient
from main import app
from models import Row, User, AuthSession, Project, hash_token
from sqlmodel import select
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_project_crud(client: AsyncClient, session):
    """
    Test Project CRUD operations and Row-Project association.
    """
    # 1. Setup User & Auth
    user = User(email="project_test@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = "test_token"
    # Use hash_token to match backend's auth verification logic
    auth = AuthSession(
        user_id=user.id, 
        email=user.email,
        session_token_hash=hash_token(token), 
        created_at=datetime.utcnow()
    )
    session.add(auth)
    await session.commit()
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Project
    response = await client.post(
        "/projects",
        json={"title": "My Trip"},
        headers=headers
    )
    assert response.status_code == 200
    project_data = response.json()
    assert project_data["title"] == "My Trip"
    project_id = project_data["id"]
    
    # 3. Create Row under Project
    response = await client.post(
        "/rows",
        json={
            "title": "Flights",
            "request_spec": {
                "item_name": "flights to japan",
                "constraints": "{}"
            },
            "project_id": project_id
        },
        headers=headers
    )
    assert response.status_code == 200
    row_data = response.json()
    assert row_data["project_id"] == project_id
    
    # 4. List Projects
    response = await client.get(
        "/projects",
        headers=headers
    )
    assert response.status_code == 200
    projects = response.json()
    # There might be projects from other tests/runs, so assert our project is present
    assert any(p["id"] == project_id for p in projects)
    # Get the project to verify details
    project = next(p for p in projects if p["id"] == project_id)
    assert project["title"] == "My Trip"
    
    # 5. Verify Row in Project (via relationship or just property check)
    # We can fetch rows and check project_id
    response = await client.get(
        "/rows",
        headers=headers
    )
    assert response.status_code == 200
    rows = response.json()
    # Find our row
    created_row = next(r for r in rows if r["id"] == row_data["id"])
    assert created_row["project_id"] == project_id

    # 6. Delete Project (and unlink rows)
    response = await client.delete(
        f"/projects/{project_id}",
        headers=headers
    )
    assert response.status_code == 200
    
    # Verify Row still exists but has project_id = null
    response = await client.get(f"/rows/{row_data['id']}", headers=headers)
    assert response.status_code == 200
    updated_row = response.json()
    assert updated_row["project_id"] is None
