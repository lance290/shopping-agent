import pytest
from fastapi.testclient import TestClient
from main import app
from routes.checkout import _get_app_base
from fastapi import Request

def test_get_app_base_origin():
    # Test Origin header
    scope = {"type": "http", "headers": [(b"origin", b"https://buy-anything.com")]}
    request = Request(scope)
    assert _get_app_base(request) == "https://buy-anything.com"

def test_get_app_base_referer():
    # Test Referer header (fallback)
    scope = {"type": "http", "headers": [(b"referer", b"https://dev.buy-anything.com/path/to/page")]}
    request = Request(scope)
    assert _get_app_base(request) == "https://dev.buy-anything.com"

def test_get_app_base_fallback_env(monkeypatch):
    # Test fallback to env var
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3003")
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    assert _get_app_base(request) == "http://localhost:3003"
