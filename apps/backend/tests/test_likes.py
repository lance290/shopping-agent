
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_likes_crud(client: AsyncClient, auth_user_and_token, test_bid):
    """Test full like CRUD via Bid.is_liked (likes stored directly on the bid)."""
    user, token = auth_user_and_token
    bid = test_bid
    bid_id = bid.id
    row_id = bid.row_id

    # 1. Like via toggle
    like_res = await client.post(
        f"/likes/{bid_id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert like_res.status_code == 200
    assert like_res.json()["is_liked"] is True
    assert like_res.json()["bid_id"] == bid_id

    # 2. Toggle again → unlike
    unlike_res = await client.post(
        f"/likes/{bid_id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert unlike_res.status_code == 200
    assert unlike_res.json()["is_liked"] is False

    # 3. Like via POST /likes
    like_res2 = await client.post(
        "/likes",
        json={"bid_id": bid_id, "row_id": row_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert like_res2.status_code == 200
    assert like_res2.json()["is_liked"] is True

    # 4. Duplicate blocked
    dup_res = await client.post(
        "/likes",
        json={"bid_id": bid_id, "row_id": row_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dup_res.status_code == 409

    # 5. List likes for row
    list_res = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    likes = list_res.json()
    assert len(likes) == 1
    assert likes[0]["bid_id"] == bid_id

    # 6. Unlike via DELETE
    del_res = await client.delete(
        f"/likes?bid_id={bid_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200

    # 7. Verify deletion
    list_res_2 = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert len(list_res_2.json()) == 0
