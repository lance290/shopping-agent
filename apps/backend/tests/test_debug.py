import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_e2e_create_row_and_fetch_debug(client, auth_user_and_token, session):
    user, token = auth_user_and_token
    resp = await client.post(
        "/rows",
        json={"title": "Standing desk", "status": "sourcing", "request_spec": {"item_name": "Standing desk", "constraints": "[]", "quantity": 1}},
        headers={"Authorization": f"Bearer {token}"},
    )
    print("STATUS", resp.status_code)
    print("DATA", resp.json())
    assert resp.status_code in (200, 201)
