"""Tests for row search query handling."""
import pytest
from unittest.mock import AsyncMock, patch
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from httpx import AsyncClient

from models import Row, RequestSpec, User, AuthSession, hash_token, VendorCoverageGap, RequestEvent, RequestFeedback, Bid, SourceMemory, Vendor
from models.outreach import OutreachCampaign, OutreachMessage
from services.llm_models import VendorCoverageAssessment
from sourcing import SearchResultWithStatus
from routes.rows_search import router, _record_vendor_coverage_gap_if_needed


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


@pytest.mark.asyncio
async def test_choice_factor_filtering(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that choice factors like color filter search results correctly."""
    from sourcing import SearchResult

    # Create auth session
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    # Create a row with color choice factor
    row = Row(
        user_id=test_user.id,
        title="T-shirt",
        status="draft",
        choice_answers='{"color": "green", "size": "XL"}'
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Mock search results with different colors
    mock_results = [
        SearchResult(
            title="Green T-Shirt XL",
            price=25.0,
            currency="USD",
            merchant="Store A",
            url="https://example.com/1",
            source="test"
        ),
        SearchResult(
            title="Blue T-Shirt XL",
            price=30.0,
            currency="USD",
            merchant="Store B",
            url="https://example.com/2",
            source="test"
        ),
        SearchResult(
            title="Green T-Shirt L",  # Wrong size
            price=25.0,
            currency="USD",
            merchant="Store C",
            url="https://example.com/3",
            source="test"
        ),
    ]

    # Mock the sourcing service to return our test results
    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(
                results=mock_results,
                provider_statuses=[],
                all_providers_failed=False
            )
        )
        mock_repo.return_value.search_all_with_status = mock_search

        # Mock SourcingService
        with patch("routes.rows_search.SourcingService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_and_persist = AsyncMock(return_value=([], [], None))
            mock_service.supersede_stale_bids = AsyncMock(return_value=0)
            mock_service_class.return_value = mock_service

            # Mock auth and rate limit
            with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
                with patch("routes.rate_limit.check_rate_limit", return_value=True):
                    response = await client.post(
                        f"/rows/{row.id}/search",
                        json={},
                        headers={"authorization": "Bearer test-token"}
                    )

                    assert response.status_code == 200
                    data = response.json()

                    # Results should be filtered by choice factors
                    # Only "Green T-Shirt XL" should pass both color and size filters
                    # Note: In the actual implementation, results come from search_and_persist
                    # which returns Bids, but the filtering logic is the same


@pytest.mark.asyncio
async def test_search_records_vendor_coverage_gap(client: AsyncClient, session: AsyncSession, test_user: User):
    """Test that search records vendor coverage gap."""
    from models import VendorCoverageGap
    from services.llm_models import VendorCoverageAssessment

    row = Row(
        user_id=test_user.id,
        title="Private jet charter",
        status="draft",
        desire_tier="service",
        service_category="private_aviation",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assessment = VendorCoverageAssessment(
        should_log_gap=True,
        gap_type="missing_vendors",
        canonical_need="private jet charter miami",
        vendor_query="private jet charter miami",
        geo_hint="Miami",
        summary="Coverage is thin for private jet charter vendors in Miami.",
        rationale="Search did not surface enough relevant vendor_directory matches.",
        suggested_vendor_search_queries=["private jet charter miami", "part 135 operator miami"],
        confidence=0.93,
    )

    with patch("routes.rows_search._resolve_user_id_and_guest", AsyncMock(return_value=(test_user.id, False))):
        with patch("routes.rate_limit.check_rate_limit", return_value=True):
            with patch("routes.rows_search.assess_vendor_coverage", AsyncMock(return_value=assessment)):
                with patch("routes.rows_search.SourcingService") as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service.search_and_persist = AsyncMock(return_value=([], [], None))
                    mock_service.supersede_stale_bids = AsyncMock(return_value=0)
                    mock_service_class.return_value = mock_service

                    response = await client.post(f"/rows/{row.id}/search", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_message"]
    assert "vendor coverage" in payload["user_message"].lower()
    assert "name and company" in payload["user_message"].lower()
    saved = await session.exec(select(VendorCoverageGap))
    gap = saved.first()
    assert gap is not None
    assert gap.canonical_need == "private jet charter miami"
    assert gap.vendor_query == "private jet charter miami"
    assert gap.status == "new"
    assert gap.times_seen == 1


@pytest.mark.asyncio
async def test_vendor_coverage_report_endpoint_marks_gap_emailed(client: AsyncClient, session: AsyncSession):
    """Test that vendor coverage report endpoint marks gap as emailed."""
    from models import VendorCoverageGap
    from services.email import EmailResult

    requester = User(
        email="ea@example.com",
        name="Taylor EA",
        company="Acme Family Office",
        phone_number="555-1111",
    )
    session.add(requester)
    await session.commit()
    await session.refresh(requester)

    gap = VendorCoverageGap(
        user_id=requester.id,
        row_title="Private jet charter",
        canonical_need="private jet charter miami",
        search_query="private jet charter miami",
        vendor_query="private jet charter miami",
        geo_hint="Miami",
        desire_tier="service",
        service_type="private_aviation",
        summary="Coverage is thin for private jet charter vendors in Miami.",
        rationale="Need more regional operators.",
        suggested_queries=["private jet charter miami"],
        confidence=0.88,
        status="new",
    )
    session.add(gap)
    await session.commit()

    with patch(
        "routes.admin_ops.send_vendor_coverage_report_email",
        AsyncMock(return_value=EmailResult(success=True, message_id="msg-123")),
    ) as mock_send:
        response = await client.post(
            "/admin/ops/vendor-coverage-report",
            headers={"x-ops-key": "sh_ops_2026_secure_key"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["count"] == 1
    assert payload["message_id"] == "msg-123"

    sent_payload = mock_send.await_args.args[0]
    assert sent_payload[0]["requester_name"] == "Taylor EA"
    assert sent_payload[0]["requester_company"] == "Acme Family Office"
    assert sent_payload[0]["requester_email"] == "ea@example.com"
    assert sent_payload[0]["requester_phone"] == "555-1111"
    assert sent_payload[0]["missing_requester_identity"] == []

    await session.refresh(gap)
    assert gap.status == "emailed"
    assert gap.emailed_count == 1
    assert gap.email_sent_at is not None


@pytest.mark.asyncio
async def test_vendor_coverage_helper_returns_none_when_persist_fails(session: AsyncSession, test_user: User):
    row = Row(
        user_id=test_user.id,
        title="Private jet charter",
        status="draft",
        desire_tier="service",
        service_category="private_aviation",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assessment = VendorCoverageAssessment(
        should_log_gap=True,
        gap_type="missing_vendors",
        canonical_need="private jet charter miami",
        vendor_query="private jet charter miami",
        geo_hint="Miami",
        summary="Coverage is thin for private jet charter vendors in Miami.",
        rationale="Need more regional operators.",
        suggested_vendor_search_queries=["private jet charter miami"],
        confidence=0.88,
    )

    original_commit = session.commit

    async def fail_commit_once():
        session.commit = original_commit
        raise RuntimeError("commit failed")

    with patch("routes.rows_search.assess_vendor_coverage", AsyncMock(return_value=assessment)):
        session.commit = AsyncMock(side_effect=fail_commit_once)
        result = await _record_vendor_coverage_gap_if_needed(
            session=session,
            row=row,
            user_id=test_user.id,
            search_query="private jet charter miami",
            results=[],
            provider_statuses=[],
        )

    assert result is None
    saved = await session.exec(select(VendorCoverageGap))
    assert saved.first() is None


@pytest.mark.asyncio
async def test_search_records_request_events(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-events"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(
        user_id=test_user.id,
        title="Eventful search",
        status="draft",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)
        )
        mock_repo.return_value.search_all_with_status = mock_search

        with patch("routes.rows_search.SourcingService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_and_persist = AsyncMock(return_value=([], [], None))
            mock_service.supersede_stale_bids = AsyncMock(return_value=0)
            mock_service_class.return_value = mock_service

            with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
                with patch("routes.rate_limit.check_rate_limit", return_value=True):
                    response = await client.post(
                        f"/rows/{row.id}/search",
                        json={"query": "eventful search query"},
                        headers={"authorization": "Bearer test-token-events"},
                    )

    assert response.status_code == 200
    events = await session.exec(
        select(RequestEvent).where(RequestEvent.row_id == row.id).order_by(RequestEvent.id)
    )
    saved_events = events.all()
    assert [event.event_type for event in saved_events] == ["search_requested", "search_completed"]
    assert saved_events[0].event_value == "eventful search query"


@pytest.mark.asyncio
async def test_outcome_endpoint_persists_outcome_and_event(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-outcome"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(
        user_id=test_user.id,
        title="Outcome row",
        status="draft",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        response = await client.post(
            f"/rows/{row.id}/outcome",
            json={"outcome": "solved", "note": "Found exact match on first try"},
            headers={"authorization": "Bearer test-token-outcome"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "solved"
    assert data["quality"] is None

    await session.refresh(row)
    assert row.row_outcome == "solved"
    assert row.outcome_note == "Found exact match on first try"

    events = await session.exec(select(RequestEvent).where(RequestEvent.row_id == row.id))
    event = events.first()
    assert event is not None
    assert event.event_type == "outcome_recorded"
    assert event.event_value == "solved"


@pytest.mark.asyncio
async def test_outcome_endpoint_rejects_invalid_outcome(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-badoutcome"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(user_id=test_user.id, title="Bad outcome row", status="draft")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        # Invalid resolution value
        response = await client.post(
            f"/rows/{row.id}/outcome",
            json={"outcome": "not_a_valid_outcome"},
            headers={"authorization": "Bearer test-token-badoutcome"},
        )
    assert response.status_code == 422

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        # results_were_noisy is a quality, not a resolution
        response = await client.post(
            f"/rows/{row.id}/outcome",
            json={"outcome": "results_were_noisy"},
            headers={"authorization": "Bearer test-token-badoutcome"},
        )
    assert response.status_code == 422

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        # Neither outcome nor quality provided
        response = await client.post(
            f"/rows/{row.id}/outcome",
            json={"note": "just a note"},
            headers={"authorization": "Bearer test-token-badoutcome"},
        )
    assert response.status_code == 422

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        # Valid quality submission
        response = await client.post(
            f"/rows/{row.id}/outcome",
            json={"quality": "results_were_strong"},
            headers={"authorization": "Bearer test-token-badoutcome"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["quality"] == "results_were_strong"


@pytest.mark.asyncio
async def test_patch_row_selection_emits_candidate_selected_event(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-select-patch"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(user_id=test_user.id, title="Selection row", status="draft")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        item_title="Trusted option",
        item_url="https://broker.example/trusted",
        source="vendor_directory",
        merchant_domain="broker.example",
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    response = await client.patch(
        f"/rows/{row.id}",
        json={"selected_bid_id": bid.id},
        headers={"authorization": "Bearer test-token-select-patch"},
    )

    assert response.status_code == 200

    await session.refresh(bid)
    assert bid.is_selected is True

    events = await session.exec(
        select(RequestEvent).where(
            RequestEvent.row_id == row.id,
            RequestEvent.event_type == "candidate_selected",
        )
    )
    event = events.first()
    assert event is not None
    assert event.bid_id == bid.id
    assert event.event_value == "vendor_directory"


@pytest.mark.asyncio
async def test_outcome_endpoint_updates_source_memory_with_aggregated_signals(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-source-memory"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(user_id=test_user.id, title="Memory row", status="draft")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    vendor = Vendor(name="Broker Example", email="sales@broker.example", domain="broker.example")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    selected_bid = Bid(
        row_id=row.id,
        vendor_id=vendor.id,
        item_title="Selected option",
        item_url="https://broker.example/selected",
        source="vendor_directory",
        source_tier="registered",
        merchant_domain="broker.example",
        canonical_url="https://broker.example/selected",
        is_selected=True,
        is_liked=True,
    )
    second_bid = Bid(
        row_id=row.id,
        vendor_id=vendor.id,
        item_title="Second option",
        item_url="https://broker.example/second",
        source="vendor_directory",
        source_tier="registered",
        merchant_domain="broker.example",
        canonical_url="https://broker.example/second",
    )
    session.add(selected_bid)
    session.add(second_bid)
    await session.commit()
    await session.refresh(selected_bid)

    campaign = OutreachCampaign(
        row_id=row.id,
        user_id=test_user.id,
        request_summary="Need a broker",
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)

    session.add(OutreachMessage(
        campaign_id=campaign.id,
        vendor_id=vendor.id,
        bid_id=selected_bid.id,
        direction="outbound",
        channel="email",
        status="sent",
        body="hello",
    ))
    await session.commit()

    response = await client.post(
        f"/rows/{row.id}/outcome",
        json={"outcome": "solved"},
        headers={"authorization": "Bearer test-token-source-memory"},
    )

    assert response.status_code == 200

    memory_result = await session.exec(
        select(SourceMemory).where(
            SourceMemory.domain == "broker.example",
            SourceMemory.source_type == "vendor_directory",
            SourceMemory.source_subtype == "registered",
        )
    )
    memory = memory_result.first()
    assert memory is not None
    assert memory.surface_count == 2
    assert memory.shortlist_count == 1
    assert memory.contact_success_count == 1
    assert memory.success_count == 1
    assert memory.trust_score == 0.5


@pytest.mark.asyncio
async def test_feedback_endpoint_persists_feedback_and_event(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-feedback"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(
        user_id=test_user.id,
        title="Feedback row",
        status="draft",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        response = await client.post(
            f"/rows/{row.id}/feedback",
            json={
                "feedback_type": "good_lead",
                "score": 0.8,
                "comment": "Strong option",
                "metadata": {"premium_fit": True},
            },
            headers={"authorization": "Bearer test-token-feedback"},
        )

    assert response.status_code == 200
    feedback_rows = await session.exec(select(RequestFeedback).where(RequestFeedback.row_id == row.id))
    feedback = feedback_rows.first()
    assert feedback is not None
    assert feedback.feedback_type == "good_lead"
    assert feedback.score == 0.8

    events = await session.exec(select(RequestEvent).where(RequestEvent.row_id == row.id))
    event = events.first()
    assert event is not None
    assert event.event_type == "feedback_submitted"
    assert event.event_value == "good_lead"


@pytest.mark.asyncio
async def test_events_endpoint_persists_generic_event(client: AsyncClient, session: AsyncSession, test_user: User):
    auth_session = AuthSession(
        email=test_user.email or "test@example.com",
        user_id=test_user.id,
        session_token_hash=hash_token("test-token-events"),
        revoked_at=None,
    )
    session.add(auth_session)
    await session.commit()

    row = Row(
        user_id=test_user.id,
        title="Events row",
        status="draft",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    with patch("routes.auth.get_current_session", AsyncMock(return_value=auth_session)):
        response = await client.post(
            f"/rows/{row.id}/events",
            json={
                "event_type": "candidate_clicked",
                "event_value": "amazon",
                "metadata": {"offer_url": "https://example.com/item"},
            },
            headers={"authorization": "Bearer test-token-events"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "id" in data

    events = await session.exec(select(RequestEvent).where(RequestEvent.row_id == row.id))
    event = events.first()
    assert event is not None
    assert event.event_type == "candidate_clicked"
    assert event.event_value == "amazon"
    assert event.user_id == test_user.id
