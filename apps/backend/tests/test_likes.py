
import pytest


@pytest.mark.asyncio
async def test_likes_crud(client, monkeypatch):
    # 1. Setup user & session
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    phone = "+16505550113"
    mint_res = await client.post("/test/mint-session", json={"phone": phone})
    assert mint_res.status_code == 200
    token = mint_res.json()["session_token"]
    
    # 2. Create a row to like items in
    row_res = await client.post(
        "/rows",
        json={
            "title": "Test Row for Likes",
            "status": "sourcing",
            "request_spec": {
                "item_name": "Test Item",
                "constraints": "{}"
            }
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert row_res.status_code == 200
    row_data = row_res.json()
    row_id = row_data["id"]

    # 3. Create a Like (by URL)
    like_payload = {
        "row_id": row_id,
        "offer_url": "https://example.com/awesome-deal"
    }
    create_res = await client.post(
        "/likes",
        json=like_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_res.status_code == 200
    like_data = create_res.json()
    assert like_data["offer_url"] == "https://example.com/awesome-deal"
    assert like_data["row_id"] == row_id
        
    # 4. Verify duplicate like is blocked
    dup_res = await client.post(
        "/likes",
        json=like_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dup_res.status_code == 409

    # 5. List likes
    list_res = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    likes = list_res.json()
    assert len(likes) == 1
    assert likes[0]["offer_url"] == "https://example.com/awesome-deal"

    # 6. Delete like
    del_res = await client.delete(
        f"/likes?row_id={row_id}&offer_url=https://example.com/awesome-deal",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200

    # 7. Verify deletion
    list_res_2 = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert len(list_res_2.json()) == 0
