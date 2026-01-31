"""Tests for Scale SERP (Google Shopping) provider."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from sourcing.repository import ScaleSerpProvider, SearchResult


class TestScaleSerpProvider:
    """Test suite for ScaleSerpProvider."""

    def test_init_sets_api_key_and_base_url(self):
        """Provider initializes with correct API key and base URL."""
        provider = ScaleSerpProvider("test_api_key")
        assert provider.api_key == "test_api_key"
        assert provider.base_url == "https://api.scaleserp.com/search"

    @pytest.mark.asyncio
    async def test_search_builds_correct_params(self):
        """Search builds correct API parameters."""
        provider = ScaleSerpProvider("test_key")
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = {"shopping_results": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            await provider.search("Bianchi bicycle", min_price=500, max_price=5000)
            
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            
            assert params["api_key"] == "test_key"
            assert params["q"] == "Bianchi bicycle"
            assert params["search_type"] == "shopping"
            assert params["location"] == "United States"
            assert params["shopping_price_min"] == 500
            assert params["shopping_price_max"] == 5000

    @pytest.mark.asyncio
    async def test_search_omits_price_params_when_not_provided(self):
        """Search omits price params when not specified."""
        provider = ScaleSerpProvider("test_key")
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = {"shopping_results": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            await provider.search("laptop")
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            
            assert "shopping_price_min" not in params
            assert "shopping_price_max" not in params

    @pytest.mark.asyncio
    async def test_search_parses_shopping_results(self):
        """Search correctly parses shopping results from API response."""
        provider = ScaleSerpProvider("test_key")
        
        mock_api_response = {
            "shopping_results": [
                {
                    "title": "Bianchi Oltre Pro",
                    "price": "$4,800.00",
                    "link": "https://example.com/bike1",
                    "source": "Bike Shop",
                    "thumbnail": "https://example.com/img1.jpg",
                    "rating": 4.5,
                    "reviews": 120
                },
                {
                    "title": "Bianchi Sprint",
                    "price": "$2,500.00",
                    "url": "https://example.com/bike2",  # alternative field name
                    "merchant": "Cycle World",  # alternative field name
                    "image": "https://example.com/img2.jpg",  # alternative field name
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await provider.search("Bianchi")
            
            assert len(results) == 2
            
            # First result
            assert results[0].title == "Bianchi Oltre Pro"
            assert results[0].price == 4800.0
            assert results[0].url == "https://example.com/bike1"
            assert results[0].merchant == "Bike Shop"
            assert results[0].image_url == "https://example.com/img1.jpg"
            assert results[0].rating == 4.5
            assert results[0].reviews_count == 120
            assert results[0].source == "google_shopping"
            
            # Second result with alternative field names
            assert results[1].title == "Bianchi Sprint"
            assert results[1].price == 2500.0

    @pytest.mark.asyncio
    async def test_search_parses_various_price_formats(self):
        """Search correctly parses various price formats."""
        provider = ScaleSerpProvider("test_key")
        
        test_cases = [
            ({"title": "Item 1", "price": "$1,299.00"}, 1299.0),
            ({"title": "Item 2", "price": "$500"}, 500.0),
            ({"title": "Item 3", "price": "2500.50"}, 2500.50),
            ({"title": "Item 4", "extracted_price": 3000}, 3000.0),
            ({"title": "Item 5", "price": "From $799.99"}, 799.99),
            ({"title": "Item 6", "price": None}, 0.0),
            ({"title": "Item 7"}, 0.0),  # No price field
        ]
        
        for item, expected_price in test_cases:
            mock_api_response = {"shopping_results": [item]}
            
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.json.return_value = mock_api_response
                mock_response.raise_for_status = MagicMock()
                mock_client.get.return_value = mock_response
                
                results = await provider.search("test")
                
                assert results[0].price == expected_price, f"Failed for {item}"

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self):
        """Search returns empty list when no results."""
        provider = ScaleSerpProvider("test_key")
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = {"shopping_results": []}
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await provider.search("nonexistent product xyz123")
            
            assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_missing_shopping_results_key(self):
        """Search returns empty list when shopping_results key is missing."""
        provider = ScaleSerpProvider("test_key")
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = {"organic_results": []}  # Wrong key
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await provider.search("test")
            
            assert results == []

    @pytest.mark.asyncio
    async def test_search_raises_on_http_error(self):
        """Search raises exception on HTTP error."""
        provider = ScaleSerpProvider("test_key")
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
            )
            mock_client.get.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await provider.search("test")

    @pytest.mark.asyncio
    async def test_search_extracts_merchant_domain(self):
        """Search correctly extracts merchant domain from URL."""
        provider = ScaleSerpProvider("test_key")
        
        mock_api_response = {
            "shopping_results": [
                {
                    "title": "Test Product",
                    "price": "$100",
                    "link": "https://www.amazon.com/dp/B123456"
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await provider.search("test")
            
            assert results[0].merchant_domain == "amazon.com"

    @pytest.mark.asyncio
    async def test_search_handles_missing_url(self):
        """Search handles results with no URL gracefully."""
        provider = ScaleSerpProvider("test_key")
        
        mock_api_response = {
            "shopping_results": [
                {
                    "title": "Test Product",
                    "price": "$100"
                    # No link/url field
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            
            results = await provider.search("test")
            
            assert results[0].url == ""
            assert results[0].merchant_domain == ""
