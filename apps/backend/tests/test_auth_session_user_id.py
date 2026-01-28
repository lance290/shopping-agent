import pytest
import sys
import os

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient
from sqlmodel import select
from models import AuthSession, User
from main import app, get_session

# Note: This test assumes a working DB connection.
# In the current environment, it might be skipped if DB is down.

@pytest.mark.asyncio
async def test_auth_session_has_user_id(client: AsyncClient, session):
    # 1. Setup: Create a user
    email = "test_user_id@example.com"
    
    # Simulate the flow or insert directly
    # We'll use the auth_verify endpoint flow to test the integration
    
    # First, we need a login code (bypassing email sending for test if possible, 
    # or just inserting one manually)
    from models import AuthLoginCode
    from models import hash_token
    
    code = "123456"
    code_hash = hash_token(code)
    login_code = AuthLoginCode(email=email, code_hash=code_hash)
    session.add(login_code)
    await session.commit()
    
    # 2. Call auth/verify
    response = await client.post("/auth/verify", json={"email": email, "code": code})
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    
    # 3. Verify AuthSession has user_id
    token = data["session_token"]
    token_hash = hash_token(token)
    
    # Check session in DB
    result = await session.exec(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    auth_session = result.first()
    assert auth_session is not None
    assert auth_session.email == email
    assert auth_session.user_id is not None
    
    # Verify it links to the correct user
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    assert user is not None
    assert auth_session.user_id == user.id
