"""
Tests for Ticketmaster provider integration
"""
import pytest
from unittest.mock import AsyncMock, patch
from sourcing import TicketmasterProvider, SearchResult


@pytest.fixture
def ticketmaster_provider():
    """Create a Ticketmaster provider instance for testing"""
    return TicketmasterProvider(api_key="test_api_key")


@pytest.fixture
def mock_ticketmaster_response():
    """Sample Ticketmaster API response"""
    return {
        "_embedded": {
            "events": [
                {
                    "name": "Notre Dame vs Clemson",
                    "url": "https://www.ticketmaster.com/event/123",
                    "priceRanges": [
                        {
                            "min": 85.0,
                            "max": 250.0,
                            "currency": "USD"
                        }
                    ],
                    "dates": {
                        "start": {
                            "localDate": "2026-09-15",
                            "localTime": "19:30"
                        }
                    },
                    "_embedded": {
                        "venues": [
                            {
                                "name": "Notre Dame Stadium"
                            }
                        ]
                    },
                    "images": [
                        {
                            "url": "https://s1.ticketm.net/dam/a/123/image.jpg",
                            "width": 1024,
                            "height": 576
                        }
                    ]
                },
                {
                    "name": "Taylor Swift Concert",
                    "url": "https://www.ticketmaster.com/event/456",
                    "priceRanges": [],
                    "dates": {
                        "start": {
                            "localDate": "2026-10-20"
                        }
                    },
                    "_embedded": {
                        "venues": [
                            {
                                "name": "Madison Square Garden"
                            }
                        ]
                    },
                    "images": []
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_ticketmaster_search_success(ticketmaster_provider, mock_ticketmaster_response):
    """Test successful Ticketmaster search"""
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_ticketmaster_response
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Execute search
        results = await ticketmaster_provider.search("Notre Dame vs Clemson")

        # Assertions
        assert len(results) == 2

        # Check first result
        assert isinstance(results[0], SearchResult)
        assert "Notre Dame vs Clemson" in results[0].title
        assert "Notre Dame Stadium" in results[0].title
        assert "2026-09-15 19:30" in results[0].title
        assert results[0].price == 85.0
        assert results[0].currency == "USD"
        assert results[0].merchant == "Ticketmaster"
        assert results[0].merchant_domain == "ticketmaster.com"
        assert results[0].source == "ticketmaster"
        assert results[0].url == "https://www.ticketmaster.com/event/123"
        assert results[0].image_url is not None

        # Check second result (no price, no time)
        assert "Taylor Swift Concert" in results[1].title
        assert "Madison Square Garden" in results[1].title
        assert results[1].price == 0.0


@pytest.mark.asyncio
async def test_ticketmaster_search_no_events(ticketmaster_provider):
    """Test Ticketmaster search with no events found"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"_embedded": {}}
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        results = await ticketmaster_provider.search("nonexistent event")

        assert len(results) == 0


@pytest.mark.asyncio
async def test_ticketmaster_search_api_error(ticketmaster_provider):
    """Test Ticketmaster search with API error"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        # Simulate HTTP error
        import httpx
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=AsyncMock(), response=mock_response
        )
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        results = await ticketmaster_provider.search("any query")

        # Should return empty list on error
        assert len(results) == 0


@pytest.mark.asyncio
async def test_ticketmaster_search_malformed_event(ticketmaster_provider):
    """Test Ticketmaster search with malformed event data"""
    with patch('httpx.AsyncClient') as mock_client:
        # Event with missing URL should be skipped
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "_embedded": {
                "events": [
                    {
                        "name": "Event without URL",
                        # Missing 'url' field
                    },
                    {
                        "name": "Valid Event",
                        "url": "https://www.ticketmaster.com/event/789",
                    }
                ]
            }
        }
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        results = await ticketmaster_provider.search("test")

        # Should only return the valid event
        assert len(results) == 1
        assert "Valid Event" in results[0].title


def test_ticketmaster_provider_initialization():
    """Test Ticketmaster provider initialization"""
    provider = TicketmasterProvider(api_key="test_key")
    assert provider.api_key == "test_key"
    assert provider.base_url == "https://app.ticketmaster.com/discovery/v2/events.json"


@pytest.mark.asyncio
async def test_ticketmaster_search_with_country_code(ticketmaster_provider, mock_ticketmaster_response):
    """Test Ticketmaster search with custom country code"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_ticketmaster_response
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Execute search with custom country code
        results = await ticketmaster_provider.search("concert", country_code="CA")

        # Verify the country code was passed to the API
        call_args = mock_client_instance.get.call_args
        assert call_args[1]["params"]["countryCode"] == "CA"
        assert len(results) == 2
