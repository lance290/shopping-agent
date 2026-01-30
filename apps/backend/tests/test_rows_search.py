"""Tests for row search query handling."""
import pytest
from unittest.mock import AsyncMock, patch
from sqlmodel.ext.asyncio.session import AsyncSession
from httpx import AsyncClient

from models import Row, RequestSpec, User, AuthSession, hash_token
from sourcing import SearchResultWithStatus
from routes.rows_search import router


@pytest.mark.asyncio
async def test_user_provided_query_not_truncated(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that explicit user queries are not truncated."""
    # Create auth session
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    # Create a row
    row = Row(
        user_id=test_user.id,
        title="Short title",
        status="draft",
        choice_answers='{"min_price": "10", "max_price": "100"}'
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Mock the sourcing repository
    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        # Mock auth and rate limit
        with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
            with patch("routes.rate_limit.check_rate_limit", return_value=True):
                # Simulate a long user query
                long_query = "God Country Notre Dame long sleeve t-shirt with special design"

                response = await client.post(
                    f"/rows/{row.id}/search",
                    json={"query": long_query},
                    headers={"authorization": "Bearer test-token"}
                )

                # Check that the search was called with the full query (minus price patterns)
                mock_search.assert_called_once()
                called_query = mock_search.call_args[0][0]

                # The query should NOT be truncated to 8 words
                # It should preserve all the user's keywords
                assert "God" in called_query
                assert "Country" in called_query
                assert "Notre" in called_query
                assert "Dame" in called_query
                assert "long" in called_query
                assert "sleeve" in called_query
                assert "t-shirt" in called_query
                assert "special" in called_query
                assert "design" in called_query


@pytest.mark.asyncio
async def test_constructed_query_with_constraints_limited(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that auto-constructed queries with constraints are reasonably limited."""
    # Create auth session
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token"),
        revoked_at=None,
    )
    session.add(auth_session)

    # Create a row with spec and choice answers
    row = Row(
        user_id=test_user.id,
        title="Notre Dame shirt",
        status="draft",
        choice_answers='{"min_price": "10", "max_price": "100", "size": "XL", "color": "blue"}'
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    spec = RequestSpec(
        row_id=row.id,
        item_name="Notre Dame shirt",
        constraints='{"material": "cotton", "style": "long sleeve"}'
    )
    session.add(spec)
    await session.commit()

    # Mock the sourcing repository
    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        # Mock auth and rate limit
        with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
            with patch("routes.rate_limit.check_rate_limit", return_value=True):
                # No explicit query - will use row.title + constraints + choice_answers
                response = await client.post(
                    f"/rows/{row.id}/search",
                    json={},
                    headers={"authorization": "Bearer test-token"}
                )

                # Check that the search was called
                mock_search.assert_called_once()
                called_query = mock_search.call_args[0][0]

                # The query should be limited to 12 words and exclude price patterns
                words = called_query.split()
                assert len(words) <= 12

                # Should NOT contain price info (removed by sanitization)
                assert "$" not in called_query

                # Should still contain the core item name
                assert "Notre" in called_query or "Dame" in called_query or "shirt" in called_query


@pytest.mark.asyncio
async def test_short_user_query_preserved(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that short user queries are fully preserved."""
    # Create auth session
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    # Create a row
    row = Row(
        user_id=test_user.id,
        title="Test",
        status="draft"
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Mock the sourcing repository
    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        # Mock auth and rate limit
        with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
            with patch("routes.rate_limit.check_rate_limit", return_value=True):
                short_query = "God Country Notre Dame"

                response = await client.post(
                    f"/rows/{row.id}/search",
                    json={"query": short_query},
                    headers={"authorization": "Bearer test-token"}
                )

                # Check that the search was called with the exact query
                mock_search.assert_called_once()
                called_query = mock_search.call_args[0][0]

                # Should preserve all words
                assert "God" in called_query
                assert "Country" in called_query
                assert "Notre" in called_query
                assert "Dame" in called_query


@pytest.mark.asyncio
async def test_price_patterns_removed_from_user_query(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that price patterns are sanitized from user queries."""
    # Create auth session
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    # Create a row
    row = Row(
        user_id=test_user.id,
        title="Test",
        status="draft"
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Mock the sourcing repository
    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        # Mock auth and rate limit
        with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
            with patch("routes.rate_limit.check_rate_limit", return_value=True):
                # User query with price patterns
                query_with_price = "Notre Dame shirt under $50 (blue)"

                response = await client.post(
                    f"/rows/{row.id}/search",
                    json={"query": query_with_price},
                    headers={"authorization": "Bearer test-token"}
                )

                # Check that the search was called
                mock_search.assert_called_once()
                called_query = mock_search.call_args[0][0]

                # Price patterns should be removed
                assert "$50" not in called_query
                assert "under" not in called_query.lower() or "$" not in called_query

                # Parentheses should be removed
                assert "(" not in called_query
                assert ")" not in called_query

                # Core search terms should remain
                assert "Notre" in called_query
                assert "Dame" in called_query
                assert "shirt" in called_query
                assert "blue" in called_query
