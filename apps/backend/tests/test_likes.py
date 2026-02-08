
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_likes_crud(client: AsyncClient, auth_user_and_token, test_bid):
    """Test like toggle via simplified POST /likes/{bid_id}/toggle endpoint."""
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

    # 2. Verify like persisted - list likes for row
    list_res = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    likes = list_res.json()
    assert len(likes) == 1
    assert likes[0]["bid_id"] == bid_id
    assert likes[0]["is_liked"] is True

    # 3. Toggle again → unlike
    unlike_res = await client.post(
        f"/likes/{bid_id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert unlike_res.status_code == 200
    assert unlike_res.json()["is_liked"] is False

    # 4. Verify unliked - list should be empty
    list_res_2 = await client.get(
        f"/likes?row_id={row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res_2.status_code == 200
    assert len(list_res_2.json()) == 0

    # 5. Toggle back to liked
    like_res3 = await client.post(
        f"/likes/{bid_id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert like_res3.status_code == 200
    assert like_res3.json()["is_liked"] is True
