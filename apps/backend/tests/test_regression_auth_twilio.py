import pytest
import os
from fastapi.testclient import TestClient
from main import app
from routes.auth import send_verification_sms
import routes.auth as auth_module

# Test the unit behavior of send_verification_sms
@pytest.mark.asyncio
async def test_send_verification_sms_missing_dependency(monkeypatch):
    """
    Regression test for the issue where TWILIO_VERIFY_SERVICE_SID is set,
    but the twilio dependency itself is missing (Client is None),
    causing send_verification_sms to return False which bubbles up to a 500.
    """
    # Force E2E and PYTEST vars off so it runs real logic
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("E2E_TEST_MODE", raising=False)
    
    # Mock environment to have only the service SID
    monkeypatch.setenv("TWILIO_VERIFY_SERVICE_SID", "VA1234567890")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    
    # Mock Client to simulate missing dependency
    original_client = auth_module.Client
    auth_module.Client = None
    
    try:
        # It should return False because it's configured but broken
        result = await send_verification_sms("+15555555555", "123456")
        assert result is False
    finally:
        # Restore
        auth_module.Client = original_client


@pytest.mark.asyncio
async def test_send_verification_sms_missing_all_credentials(monkeypatch):
    """
    Test behavior when nothing is set, shouldn't crash
    """
    # Force E2E and PYTEST vars off so it runs real logic
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("E2E_TEST_MODE", raising=False)
    
    monkeypatch.delenv("TWILIO_VERIFY_SERVICE_SID", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)
    
    # This should return True because it defaults to standard log mode when empty
    result = await send_verification_sms("+15555555555", "123456")
    assert result is True

