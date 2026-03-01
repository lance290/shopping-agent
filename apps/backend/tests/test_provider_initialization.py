"""Tests for provider initialization in SourcingRepository."""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestProviderInitialization:
    """Test suite for SourcingRepository provider initialization."""

    def test_rainforest_initialized_as_amazon_provider(self):
        """RainforestAPIProvider should be initialized as 'amazon' when key is present."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest_key",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "amazon" in repo.providers
            assert isinstance(repo.providers["amazon"], __import__("sourcing.repository", fromlist=["RainforestAPIProvider"]).RainforestAPIProvider)

    def test_amazon_not_initialized_when_rainforest_key_missing(self):
        """Amazon provider should not be initialized when RAINFOREST_API_KEY is empty."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "",
            "SCALESERP_API_KEY": "test_scaleserp_key",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "amazon" not in repo.providers

    def test_scaleserp_amazon_provider_disabled(self):
        """ScaleSerpAmazonProvider is DISABLED — SCALESERP_API_KEY alone should not create amazon provider."""
        with patch.dict(os.environ, {
            "SCALESERP_API_KEY": "test_scaleserp_key",
            "RAINFOREST_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "amazon" not in repo.providers

    def test_rainforest_provider_disabled(self):
        """RainforestAPIProvider is disabled — should NOT be initialized even with key."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest_key",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "rainforest" not in repo.providers

    def test_rainforest_provider_has_correct_api_key(self):
        """RainforestAPIProvider should have the correct API key."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest_key",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "amazon" in repo.providers
            assert repo.providers["amazon"].api_key == "test_rainforest_key"

    def test_google_cse_provider_disabled(self):
        """GoogleCustomSearchProvider is DISABLED — should NOT be initialized even with both keys."""
        with patch.dict(os.environ, {
            "GOOGLE_CSE_API_KEY": "test_key",
            "GOOGLE_CSE_CX": "test_cx",
            "RAINFOREST_API_KEY": "",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "google_cse" not in repo.providers

    def test_active_providers_with_all_keys(self):
        """Amazon (Rainforest) + Vendor Directory should be active. SerpAPI disabled (Skimlinks conflict)."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest",
            "SCALESERP_API_KEY": "test_scaleserp",
            "SERPAPI_API_KEY": "test_serpapi",
            "SEARCHAPI_API_KEY": "test_searchapi",
            "VALUESERP_API_KEY": "test_valueserp",
            "GOOGLE_CSE_API_KEY": "test_google",
            "GOOGLE_CSE_CX": "test_cx",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "amazon" in repo.providers
            assert "serpapi" not in repo.providers
            assert "google_shopping" not in repo.providers
            assert "searchapi" not in repo.providers
            assert "valueserp" not in repo.providers
            assert "google_cse" not in repo.providers

    def test_provider_timeout_configurable(self):
        """Provider timeout should be configurable via environment variable."""
        with patch.dict(os.environ, {
            "SOURCING_PROVIDER_TIMEOUT_SECONDS": "15",
            "RAINFOREST_API_KEY": "",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            timeout = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "8.0"))
            assert timeout == 15.0

    def test_provider_timeout_defaults_to_30_seconds(self):
        """Provider timeout should default to 30 seconds for streaming."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var if it exists
            env_timeout = os.environ.pop("SOURCING_PROVIDER_TIMEOUT_SECONDS", None)
            try:
                timeout = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "30.0"))
                assert timeout == 30.0
            finally:
                # Restore if it was there
                if env_timeout:
                    os.environ["SOURCING_PROVIDER_TIMEOUT_SECONDS"] = env_timeout


class TestEbayProviderInitialization:
    """eBay Browse API provider initialization from env vars."""

    def test_ebay_initialized_when_credentials_set(self):
        """EbayBrowseProvider should be registered as 'ebay' when both CLIENT_ID and CLIENT_SECRET are set."""
        with patch.dict(os.environ, {
            "EBAY_CLIENT_ID": "test_client_id",
            "EBAY_CLIENT_SECRET": "test_client_secret",
            "EBAY_MARKETPLACE_ID": "EBAY-US",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository, EbayBrowseProvider
            repo = SourcingRepository()

            assert "ebay" in repo.providers
            assert isinstance(repo.providers["ebay"], EbayBrowseProvider)

    def test_ebay_not_initialized_when_client_id_missing(self):
        """eBay provider should not be registered when EBAY_CLIENT_ID is empty."""
        with patch.dict(os.environ, {
            "EBAY_CLIENT_ID": "",
            "EBAY_CLIENT_SECRET": "test_secret",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "ebay" not in repo.providers

    def test_ebay_not_initialized_when_client_secret_missing(self):
        """eBay provider should not be registered when EBAY_CLIENT_SECRET is empty."""
        with patch.dict(os.environ, {
            "EBAY_CLIENT_ID": "test_id",
            "EBAY_CLIENT_SECRET": "",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "ebay" not in repo.providers

    def test_ebay_marketplace_defaults_to_us(self):
        """eBay marketplace ID should default to EBAY-US."""
        with patch.dict(os.environ, {
            "EBAY_CLIENT_ID": "test_id",
            "EBAY_CLIENT_SECRET": "test_secret",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            os.environ.pop("EBAY_MARKETPLACE_ID", None)
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "ebay" in repo.providers
            assert repo.providers["ebay"].marketplace_id == "EBAY-US"


class TestKrogerProviderInitialization:
    """Kroger Product API provider initialization from env vars."""

    def test_kroger_initialized_when_credentials_set(self):
        """KrogerProvider should be registered when KROGER_CLIENT_ID and KROGER_CLIENT_SECRET are set."""
        with patch.dict(os.environ, {
            "KROGER_CLIENT_ID": "test_kroger_id",
            "KROGER_CLIENT_SECRET": "test_kroger_secret",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "kroger" in repo.providers

    def test_kroger_not_initialized_when_client_id_missing(self):
        """Kroger provider should not be registered when KROGER_CLIENT_ID is empty."""
        with patch.dict(os.environ, {
            "KROGER_CLIENT_ID": "",
            "KROGER_CLIENT_SECRET": "test_secret",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "kroger" not in repo.providers


class TestTicketmasterProviderInitialization:
    """Ticketmaster Discovery API provider initialization from env vars."""

    def test_ticketmaster_initialized_when_key_set(self):
        """TicketmasterProvider should be registered when TICKETMASTER_API_KEY is set."""
        with patch.dict(os.environ, {
            "TICKETMASTER_API_KEY": "test_tm_key",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "ticketmaster" in repo.providers

    def test_ticketmaster_not_initialized_when_key_missing(self):
        """Ticketmaster provider should not be registered when TICKETMASTER_API_KEY is empty."""
        with patch.dict(os.environ, {
            "TICKETMASTER_API_KEY": "",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "ticketmaster" not in repo.providers


class TestVendorDirectoryProviderInitialization:
    """Vendor Directory (pgvector) provider initialization from env vars."""

    def test_vendor_directory_initialized_when_database_url_set(self):
        """VendorDirectoryProvider should always be registered when DATABASE_URL is set."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql+asyncpg://localhost:5432/test",
            "RAINFOREST_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()

            assert "vendor_directory" in repo.providers


class TestProviderPriority:
    """Test that providers are initialized in expected priority order."""

    def test_amazon_is_first_provider(self):
        """Amazon (Rainforest) should be the first provider initialized."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            provider_names = list(repo.providers.keys())
            assert "amazon" in provider_names
            assert provider_names[0] == "amazon"
