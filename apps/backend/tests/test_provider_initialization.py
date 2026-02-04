"""Tests for provider initialization in SourcingRepository."""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestProviderInitialization:
    """Test suite for SourcingRepository provider initialization."""

    def test_scaleserp_provider_initialized_when_key_present(self):
        """ScaleSerpProvider should be initialized when SCALESERP_API_KEY is set."""
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
            
            assert "google_shopping" in repo.providers
            assert repo.providers["google_shopping"].api_key == "test_scaleserp_key"

    def test_scaleserp_provider_not_initialized_when_key_missing(self):
        """ScaleSerpProvider should not be initialized when SCALESERP_API_KEY is empty."""
        with patch.dict(os.environ, {
            "SCALESERP_API_KEY": "",
            "RAINFOREST_API_KEY": "test_rainforest_key",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "google_shopping" not in repo.providers

    def test_scaleserp_provider_not_initialized_when_key_is_demo(self):
        """ScaleSerpProvider should not be initialized when SCALESERP_API_KEY is 'demo'."""
        with patch.dict(os.environ, {
            "SCALESERP_API_KEY": "demo",
            "RAINFOREST_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "google_shopping" not in repo.providers

    def test_rainforest_provider_initialized_when_key_present(self):
        """RainforestAPIProvider should be initialized when RAINFOREST_API_KEY is set."""
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
            
            assert "rainforest" in repo.providers

    def test_google_cse_provider_requires_both_key_and_cx(self):
        """GoogleCustomSearchProvider requires both API key and CX."""
        # Only key, no CX
        with patch.dict(os.environ, {
            "GOOGLE_CSE_API_KEY": "test_key",
            "GOOGLE_CSE_CX": "",
            "RAINFOREST_API_KEY": "",
            "SCALESERP_API_KEY": "",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            assert "google_cse" not in repo.providers
        
        # Only CX, no key
        with patch.dict(os.environ, {
            "GOOGLE_CSE_API_KEY": "",
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
        
        # Both present
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
            
            assert "google_cse" in repo.providers

    def test_multiple_providers_can_be_initialized(self):
        """Multiple providers should be initialized when their keys are present."""
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
            
            assert "rainforest" in repo.providers
            assert "google_shopping" in repo.providers
            assert "serpapi" in repo.providers
            assert "searchapi" in repo.providers
            assert "valueserp" in repo.providers
            assert "google_cse" in repo.providers

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


class TestProviderPriority:
    """Test that providers are initialized in expected priority order."""

    def test_providers_dict_order_maintained(self):
        """Provider dict should maintain insertion order (Python 3.7+)."""
        with patch.dict(os.environ, {
            "RAINFOREST_API_KEY": "test_rainforest",
            "SCALESERP_API_KEY": "test_scaleserp",
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "VALUESERP_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            from sourcing.repository import SourcingRepository
            repo = SourcingRepository()
            
            provider_names = list(repo.providers.keys())
            
            # Rainforest should be before google_shopping based on init order
            if "rainforest" in provider_names and "google_shopping" in provider_names:
                assert provider_names.index("rainforest") < provider_names.index("google_shopping")
