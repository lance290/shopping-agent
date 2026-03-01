import json
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from unittest.mock import AsyncMock, patch

from models import Row, AuthSession, User, hash_token
from sourcing import SearchResultWithStatus


@pytest.mark.asyncio
async def test_search_persists_search_intent_and_provider_query_map(
    client: AsyncClient, session: AsyncSession
):
    user = User(email="intent@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = "intent-token"
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(user_id=user.id, title="Running shoes", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    intent_payload = {
        "product_category": "running_shoes",
        "taxonomy_version": "1.0",
        "keywords": ["running", "shoes"],
        "max_price": 80,
    }
    provider_query_map = {
        "queries": {
            "rainforest": {"provider_id": "rainforest", "query": "running shoes"}
        }
    }

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        response = await client.post(
            f"/rows/{row.id}/search",
            json={
                "query": "running shoes",
                "search_intent": intent_payload,
                "provider_query_map": provider_query_map,
            },
            headers={"authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200

    persisted = await session.get(Row, row.id)
    assert persisted is not None
    raw_intent = persisted.search_intent or {}
    persisted_intent = json.loads(raw_intent) if isinstance(raw_intent, str) else raw_intent
    assert persisted_intent.get("product_category") == intent_payload["product_category"]
    assert persisted_intent.get("taxonomy_version") == intent_payload["taxonomy_version"]
    assert persisted_intent.get("max_price") == intent_payload["max_price"]
    raw_pqm = persisted.provider_query_map or {}
    persisted_pqm = json.loads(raw_pqm) if isinstance(raw_pqm, str) else raw_pqm
    assert persisted_pqm == provider_query_map
