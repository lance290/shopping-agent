import pytest
from sourcing.safety import SafetyService

def test_safety_service_clean():
    result = SafetyService.check_safety("flights to paris")
    assert result["status"] == "safe"
    assert result["reason"] is None

def test_safety_service_blocked():
    result = SafetyService.check_safety("hire a hitman")
    assert result["status"] == "blocked"
    assert "safety policies" in result["reason"]

def test_safety_service_sensitive():
    result = SafetyService.check_safety("massage services")
    assert result["status"] == "needs_review"
    assert "sensitive category" in result["reason"]

def test_safety_service_cupcake():
    # User specifically mentioned "cupcakes" as a potential code word
    # Our policy currently marks it as safe unless it's in a suspicious context context,
    # BUT for this test I actually added "cupcake" to the sensitive list based on the user request.
    result = SafetyService.check_safety("I want cupcakes")
    assert result["status"] == "needs_review"
