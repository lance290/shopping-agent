import pytest
import sys
import os
from httpx import AsyncClient
from sqlmodel import select
from models import Row, AuthSession, User

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, get_session, hash_token, generate_session_token

@pytest.mark.asyncio
async def test_rows_authorization(client: AsyncClient, session):
    # Setup: Create two users (A and B) and sessions
    user_a_email = "user_a@example.com"
    user_b_email = "user_b@example.com"
    
    # Create Users
    user_a = User(email=user_a_email)
    user_b = User(email=user_b_email)
    session.add(user_a)
    session.add(user_b)
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)
    
    # Create Sessions
    token_a = "token_a_123"
    token_b = "token_b_456"
    
    session_a = AuthSession(email=user_a_email, user_id=user_a.id, session_token_hash=hash_token(token_a))
    session_b = AuthSession(email=user_b_email, user_id=user_b.id, session_token_hash=hash_token(token_b))
    session.add(session_a)
    session.add(session_b)
    await session.commit()
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 1. Verify Unauthenticated Access is Blocked
    resp = await client.get("/rows")
    assert resp.status_code == 401
    
    # 2. User A creates a row
    row_data = {
        "title": "User A Row",
        "status": "sourcing",
        "currency": "USD",
        "request_spec": {
            "item_name": "User A Item",
            "constraints": "{}"
        }
    }
    resp = await client.post("/rows", json=row_data, headers=headers_a)
    assert resp.status_code == 200
    created_row = resp.json()
    row_id_a = created_row["id"]
    assert created_row["title"] == "User A Row"
    
    # Verify DB ownership
    db_row = await session.get(Row, row_id_a)
    assert db_row.user_id == user_a.id
    
    # 3. User A can see their row
    resp = await client.get("/rows", headers=headers_a)
    assert resp.status_code == 200
    rows_a = resp.json()
    assert len(rows_a) == 1
    assert rows_a[0]["id"] == row_id_a
    
    # 4. User B cannot see User A's row
    resp = await client.get("/rows", headers=headers_b)
    assert resp.status_code == 200
    rows_b = resp.json()
    assert len(rows_b) == 0
    
    # 5. User B cannot access User A's row by ID (404 Not Found, not 403 Forbidden to prevent leakage)
    resp = await client.get(f"/rows/{row_id_a}", headers=headers_b)
    assert resp.status_code == 404
    
    # 6. User B cannot update User A's row
    patch_data = {"title": "Hacked by B"}
    resp = await client.patch(f"/rows/{row_id_a}", json=patch_data, headers=headers_b)
    assert resp.status_code == 404
    
    # Verify title unchanged
    await session.refresh(db_row)
    assert db_row.title == "User A Row"
    
    # 7. User B cannot delete User A's row
    resp = await client.delete(f"/rows/{row_id_a}", headers=headers_b)
    assert resp.status_code == 404
    
    # Verify row still exists
    db_row = await session.get(Row, row_id_a)
    assert db_row is not None
    
    # 8. User A can delete their row
    resp = await client.delete(f"/rows/{row_id_a}", headers=headers_a)
    assert resp.status_code == 200
    
    # Verify row gone
    db_row = await session.get(Row, row_id_a)
    assert db_row is None
