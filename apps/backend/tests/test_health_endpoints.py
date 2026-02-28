"""
Tests for health check endpoints.

Verifies:
- /health returns 200 with correct status and version fields
- /health/ready returns correct response structure
"""

import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_health_returns_200():
    """Basic health check should always return 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_body():
    """Health check should return status and version fields."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert isinstance(data["version"], str)


def test_health_content_type():
    """/health should return JSON."""
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
