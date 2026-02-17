"""Tests for Ticketmaster provider integration."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sourcing import TicketmasterProvider, SearchResult


@pytest.fixture
def ticketmaster_provider():
    """Create a Ticketmaster provider instance for testing."""
    return TicketmasterProvider(api_key="test_api_key")


@pytest.fixture
def mock_ticketmaster_response():
    """Sample Ticketmaster API response."""
    return {
        "_embedded": {
            "events": [
                {
                    "name": "Notre Dame vs Clemson",
                    "url": "https://www.ticketmaster.com/event/123",
                    "priceRanges": [
                        {"min": 85.0, "max": 350.0, "currency": "USD"}
                    ],
                    "dates": {
                        "start": {
                            "localDate": "2026-09-15",
                            "localTime": "19:30:00",
                        }
                    },
                    "images": [
                        {
                            "url": "https://s1.ticketm.net/dam/a/123/image.jpg",
                            "width": 1024,
                            "height": 683,
                        }
                    ],
                    "_embedded": {
                        "venues": [{"name": "Notre Dame Stadium"}]
                    },
                },
                {
                    "name": "Clemson Tigers vs Notre Dame",
                    "url": "https://www.ticketmaster.com/event/456",
                    "priceRanges": [
                        {"min": 45.0, "max": 200.0, "currency": "USD"}
                    ],
                    "dates": {
                        "start": {
                            "localDate": "2026-10-20",
                            "localTime": "15:00:00",
                        }
                    },
                    "images": [
                        {
                            "url": "https://s1.ticketm.net/dam/a/456/image2.jpg",
                            "width": 640,
                            "height": 427,
                        }
                    ],
                    "_embedded": {
                        "venues": [{"name": "Memorial Stadium"}]
                    },
                },
            ]
        }
    }


# === Keyword guard tests ===


def test_event_query_detection(ticketmaster_provider):
    """Test that event-related queries are correctly identified."""
    assert ticketmaster_provider._is_event_query("Taylor Swift concert tickets") is True
    assert ticketmaster_provider._is_event_query("NBA game tonight") is True
    assert ticketmaster_provider._is_event_query("Broadway show") is True
    assert ticketmaster_provider._is_event_query("music festival 2026") is True
    assert ticketmaster_provider._is_event_query("UFC match tickets") is True


def test_non_event_query_detection(ticketmaster_provider):
    """Test that non-event queries are correctly filtered out."""
    assert ticketmaster_provider._is_event_query("AA batteries") is False
    assert ticketmaster_provider._is_event_query("laptop for video editing") is False
    assert ticketmaster_provider._is_event_query("private jet charter") is False
    assert ticketmaster_provider._is_event_query("running shoes") is False


@pytest.mark.asyncio
async def test_non_event_query_returns_empty(ticketmaster_provider):
    """Non-event queries should return empty without making API calls."""
    results = await ticketmaster_provider.search("AA batteries")
    assert results == []


# === API response tests ===


@pytest.mark.asyncio
async def test_search_success(ticketmaster_provider, mock_ticketmaster_response):
    """Test successful Ticketmaster search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ticketmaster_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("Notre Dame vs Clemson tickets")

    assert len(results) == 2
    assert results[0].merchant == "Ticketmaster"
    assert results[0].merchant_domain == "ticketmaster.com"
    assert results[0].source == "ticketmaster"
    assert results[0].url == "https://www.ticketmaster.com/event/123"
    assert results[0].price == 85.0
    assert "Notre Dame Stadium" in results[0].title
    assert "2026-09-15" in results[0].title
    assert results[0].image_url == "https://s1.ticketm.net/dam/a/123/image.jpg"


@pytest.mark.asyncio
async def test_search_no_events(ticketmaster_provider):
    """Test Ticketmaster search with no events found."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"_embedded": {"events": []}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("nonexistent event tickets")

    assert results == []


@pytest.mark.asyncio
async def test_search_api_error(ticketmaster_provider):
    """Test Ticketmaster search with API error."""
    import httpx

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("concert tickets")

    assert results == []


@pytest.mark.asyncio
async def test_search_malformed_event(ticketmaster_provider):
    """Test Ticketmaster search with malformed event data (no URL)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "events": [
                {
                    "name": "Broken Event",
                    # No URL — should be skipped
                },
                {
                    "name": "Good Event",
                    "url": "https://www.ticketmaster.com/event/789",
                    "dates": {"start": {"localDate": "2026-12-01"}},
                    "_embedded": {"venues": [{"name": "Good Venue"}]},
                },
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("event tickets")

    # Only the event with a URL should be returned
    assert len(results) == 1
    assert "Good Event" in results[0].title


# === Initialization tests ===


def test_provider_initialization():
    """Test Ticketmaster provider initialization."""
    provider = TicketmasterProvider(api_key="test_key")
    assert provider.api_key == "test_key"
    assert provider.base_url == "https://app.ticketmaster.com/discovery/v2/events.json"


@pytest.mark.asyncio
async def test_search_missing_embedded(ticketmaster_provider):
    """Test Ticketmaster search when _embedded key is missing."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # No _embedded
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("concert tickets")

    assert results == []


@pytest.mark.asyncio
async def test_search_event_without_price(ticketmaster_provider):
    """Test event without price ranges still returns with price=0."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "_embedded": {
            "events": [
                {
                    "name": "Free Community Event",
                    "url": "https://www.ticketmaster.com/event/free1",
                    "dates": {"start": {"localDate": "2026-07-04"}},
                    "_embedded": {"venues": [{"name": "City Park"}]},
                    # No priceRanges
                }
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        results = await ticketmaster_provider.search("community event tickets")

    assert len(results) == 1
    assert results[0].price == 0.0
    assert "City Park" in results[0].title
