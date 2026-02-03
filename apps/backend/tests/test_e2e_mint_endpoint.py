import pytest
import os
from httpx import AsyncClient
import sys

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

@pytest.mark.asyncio
async def test_mint_session_endpoint(client: AsyncClient, monkeypatch):
    # 1. Test when E2E_TEST_MODE is NOT set (should be 404)
    monkeypatch.delenv("E2E_TEST_MODE", raising=False)
    resp = await client.post("/test/mint-session", json={"phone": "+16505550110"})
    assert resp.status_code == 404
    
    # 2. Test when E2E_TEST_MODE is set (should be 200)
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    phone = "+16505550111"
    resp = await client.post("/test/mint-session", json={"phone": phone})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    assert len(data["session_token"]) > 0
    
    # Verify the token works against a protected endpoint
    token = data["session_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone_number"] == phone
