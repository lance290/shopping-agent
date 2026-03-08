"""Unit tests for services/veryfi.py — data classes, HMAC signing, config checks."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.veryfi import (
    VeryfiReceiptResult,
    VeryfiLineItem,
    VeryfiError,
    _generate_signature,
    _build_headers,
    _check_config,
    process_receipt_base64,
)


# ---------------------------------------------------------------------------
# VeryfiLineItem
# ---------------------------------------------------------------------------


def test_line_item_parses_all_fields():
    raw = {"description": "HIPPEAS CHKPEA PUFF", "total": 3.49, "quantity": 1, "price": 3.49, "sku": "123", "upc": "456"}
    item = VeryfiLineItem(raw)
    assert item.description == "HIPPEAS CHKPEA PUFF"
    assert item.total == 3.49
    assert item.quantity == 1
    assert item.unit_price == 3.49
    assert item.sku == "123"
    assert item.upc == "456"


def test_line_item_handles_missing_fields():
    item = VeryfiLineItem({})
    assert item.description == ""
    assert item.total is None
    assert item.to_dict()["description"] == ""


# ---------------------------------------------------------------------------
# VeryfiReceiptResult
# ---------------------------------------------------------------------------


def _make_raw(fraud_score=0.0, fraud_types=None, is_duplicate=False, line_items=None):
    return {
        "id": 99,
        "vendor": {"name": "Kroger", "address": "123 Main St"},
        "total": 25.49,
        "subtotal": 24.00,
        "tax": 1.49,
        "date": "2026-03-07",
        "currency_code": "USD",
        "line_items": line_items or [],
        "is_duplicate": is_duplicate,
        "meta": {"fraud": {"score": fraud_score, "types": fraud_types or []}},
    }


def test_receipt_result_parses_vendor_and_total():
    r = VeryfiReceiptResult(_make_raw())
    assert r.vendor_name == "Kroger"
    assert r.total == 25.49
    assert r.date == "2026-03-07"
    assert r.document_id == 99


def test_receipt_result_not_fraudulent_by_default():
    r = VeryfiReceiptResult(_make_raw())
    assert r.is_fraudulent is False
    assert r.fraud_flags == []


def test_receipt_result_tampered_is_fraudulent():
    r = VeryfiReceiptResult(_make_raw(fraud_types=["tampered"]))
    assert r.is_tampered is True
    assert r.is_fraudulent is True
    assert "tampered" in r.fraud_flags


def test_receipt_result_screen_is_fraudulent():
    r = VeryfiReceiptResult(_make_raw(fraud_types=["screen"]))
    assert r.is_screen is True
    assert r.is_fraudulent is True


def test_receipt_result_high_fraud_score_is_fraudulent():
    r = VeryfiReceiptResult(_make_raw(fraud_score=0.8))
    assert r.is_fraudulent is True


def test_receipt_result_duplicate_is_fraudulent():
    r = VeryfiReceiptResult(_make_raw(is_duplicate=True))
    assert r.is_fraudulent is True
    assert "duplicate_receipt" in r.fraud_flags


def test_receipt_result_parses_line_items():
    items = [
        {"description": "Milk", "total": 3.49},
        {"description": "Eggs", "total": 2.99},
    ]
    r = VeryfiReceiptResult(_make_raw(line_items=items))
    assert len(r.line_items) == 2
    assert r.line_items[0].description == "Milk"
    assert r.line_items[1].total == 2.99


def test_receipt_result_to_dict():
    r = VeryfiReceiptResult(_make_raw(line_items=[{"description": "Chips", "total": 4.99}]))
    d = r.to_dict()
    assert d["vendor_name"] == "Kroger"
    assert d["total"] == 25.49
    assert len(d["line_items"]) == 1
    assert d["is_fraudulent"] is False


# ---------------------------------------------------------------------------
# HMAC Signature
# ---------------------------------------------------------------------------


@patch("services.veryfi.VERYFI_CLIENT_SECRET", "test_secret")
def test_generate_signature_returns_hex_string():
    sig = _generate_signature('{"test": true}', 1234567890)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex digest


@patch("services.veryfi.VERYFI_CLIENT_SECRET", "test_secret")
def test_generate_signature_is_deterministic():
    sig1 = _generate_signature('{"test": true}', 1234567890)
    sig2 = _generate_signature('{"test": true}', 1234567890)
    assert sig1 == sig2


@patch("services.veryfi.VERYFI_CLIENT_SECRET", "test_secret")
def test_generate_signature_changes_with_different_timestamp():
    sig1 = _generate_signature('{"test": true}', 1111111111)
    sig2 = _generate_signature('{"test": true}', 2222222222)
    assert sig1 != sig2


# ---------------------------------------------------------------------------
# Config check
# ---------------------------------------------------------------------------


@patch("services.veryfi.VERYFI_CLIENT_ID", "")
@patch("services.veryfi.VERYFI_CLIENT_SECRET", "secret")
@patch("services.veryfi.VERYFI_USERNAME", "user")
@patch("services.veryfi.VERYFI_API_KEY", "key")
def test_check_config_raises_on_missing_client_id(monkeypatch):
    monkeypatch.delenv("VERYFI_CLIENT_ID", raising=False)
    with pytest.raises(VeryfiError, match="VERYFI_CLIENT_ID"):
        _check_config()


@patch("services.veryfi.VERYFI_CLIENT_ID", "id")
@patch("services.veryfi.VERYFI_CLIENT_SECRET", "secret")
@patch("services.veryfi.VERYFI_USERNAME", "user")
@patch("services.veryfi.VERYFI_API_KEY", "key")
def test_check_config_passes_with_all_vars():
    _check_config()  # Should not raise


@patch("services.veryfi.VERYFI_CLIENT_ID", "")
@patch("services.veryfi.VERYFI_CLIENT_SECRET", "")
@patch("services.veryfi.VERYFI_USERNAME", "")
@patch("services.veryfi.VERYFI_API_KEY", "")
def test_check_config_reads_current_env_when_module_constants_are_blank(monkeypatch):
    monkeypatch.setenv("VERYFI_CLIENT_ID", "env_id")
    monkeypatch.setenv("VERYFI_CLIENT_SECRET", "env_secret")
    monkeypatch.setenv("VERYFI_USERNAME", "env_user")
    monkeypatch.setenv("VERYFI_API_KEY", "env_key")
    _check_config()


# ---------------------------------------------------------------------------
# process_receipt_base64 (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("services.veryfi.VERYFI_CLIENT_ID", "id")
@patch("services.veryfi.VERYFI_CLIENT_SECRET", "secret")
@patch("services.veryfi.VERYFI_USERNAME", "user")
@patch("services.veryfi.VERYFI_API_KEY", "key")
async def test_process_receipt_base64_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = _make_raw(line_items=[{"description": "Milk", "total": 3.49}])

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.veryfi.httpx.AsyncClient", return_value=mock_client):
        result = await process_receipt_base64("dGVzdA==")

    assert isinstance(result, VeryfiReceiptResult)
    assert len(result.line_items) == 1
    assert result.line_items[0].description == "Milk"


@pytest.mark.asyncio
@patch("services.veryfi.VERYFI_CLIENT_ID", "id")
@patch("services.veryfi.VERYFI_CLIENT_SECRET", "secret")
@patch("services.veryfi.VERYFI_USERNAME", "user")
@patch("services.veryfi.VERYFI_API_KEY", "key")
async def test_process_receipt_base64_api_error_raises():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.veryfi.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(VeryfiError, match="500"):
            await process_receipt_base64("dGVzdA==")
