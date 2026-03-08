"""
Veryfi receipt OCR and fraud detection service.

Wraps the Veryfi API v8 for:
  - Receipt image processing (line-item extraction)
  - Fraud detection (tamper, screen, AI-generated)

Auth: CLIENT-ID header + apikey Authorization + HMAC signature.
Docs: https://docs.veryfi.com/api/getting-started/authentication/

Policy: NO fallback to Gemini or any other OCR. If Veryfi fails,
we return an error and the caller handles it gracefully.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (loaded once from env)
# ---------------------------------------------------------------------------

VERYFI_API_BASE_URL = os.getenv("VERYFI_API_BASE_URL", "https://api.veryfi.com/")
VERYFI_CLIENT_ID = os.getenv("VERYFI_CLIENT_ID", "")
VERYFI_CLIENT_SECRET = os.getenv("VERYFI_CLIENT_SECRET", "")
VERYFI_USERNAME = os.getenv("VERYFI_USERNAME", "")
VERYFI_API_KEY = os.getenv("VERYFI_API_KEY", "")

DOCUMENTS_ENDPOINT = "api/v8/partner/documents/"

TIMEOUT_SECONDS = 30


def _client_id() -> str:
    return VERYFI_CLIENT_ID or os.getenv("VERYFI_CLIENT_ID", "")


def _client_secret() -> str:
    return VERYFI_CLIENT_SECRET or os.getenv("VERYFI_CLIENT_SECRET", "")


def _username() -> str:
    return VERYFI_USERNAME or os.getenv("VERYFI_USERNAME", "")


def _api_key() -> str:
    return VERYFI_API_KEY or os.getenv("VERYFI_API_KEY", "")


def _api_base_url() -> str:
    return VERYFI_API_BASE_URL or os.getenv("VERYFI_API_BASE_URL", "https://api.veryfi.com/")


# ---------------------------------------------------------------------------
# HMAC Signature (required by Veryfi for POST requests)
# ---------------------------------------------------------------------------


def _generate_signature(payload_str: str, timestamp: int) -> str:
    """
    Generate X-Veryfi-Request-Signature for a POST request.

    signature = HMAC-SHA256(CLIENT_SECRET, timestamp + payload_json)
    """
    msg = str(timestamp) + payload_str
    return hmac.new(
        _client_secret().encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_headers(payload_str: str) -> Dict[str, str]:
    """Build all required Veryfi auth headers."""
    timestamp = int(time.time() * 1000)  # ms since epoch
    signature = _generate_signature(payload_str, timestamp)
    return {
        "CLIENT-ID": _client_id(),
        "Authorization": f"apikey {_username()}:{_api_key()}",
        "X-Veryfi-Request-Timestamp": str(timestamp),
        "X-Veryfi-Request-Signature": signature,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Data classes for structured results
# ---------------------------------------------------------------------------


class VeryfiLineItem:
    """A single line item from a parsed receipt."""

    def __init__(self, raw: Dict[str, Any]):
        self.description: str = raw.get("description", "")
        self.total: Optional[float] = raw.get("total")
        self.quantity: Optional[float] = raw.get("quantity")
        self.unit_price: Optional[float] = raw.get("price")
        self.sku: Optional[str] = raw.get("sku")
        self.upc: Optional[str] = raw.get("upc")
        self.raw = raw

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "total": self.total,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "sku": self.sku,
            "upc": self.upc,
        }


class VeryfiReceiptResult:
    """Structured result from Veryfi document processing."""

    def __init__(self, raw_response: Dict[str, Any]):
        self.raw = raw_response
        self.document_id: Optional[int] = raw_response.get("id")
        self.vendor_name: str = (raw_response.get("vendor", {}) or {}).get("name", "")
        self.vendor_address: str = (raw_response.get("vendor", {}) or {}).get("address", "")
        self.total: Optional[float] = raw_response.get("total")
        self.subtotal: Optional[float] = raw_response.get("subtotal")
        self.tax: Optional[float] = raw_response.get("tax")
        self.date: Optional[str] = raw_response.get("date")
        self.currency_code: str = raw_response.get("currency_code", "USD")

        # Line items
        raw_items = raw_response.get("line_items", []) or []
        self.line_items: List[VeryfiLineItem] = [VeryfiLineItem(i) for i in raw_items]

        # Fraud indicators
        self.is_duplicate: bool = raw_response.get("is_duplicate", False)
        meta = raw_response.get("meta", {}) or {}
        fraud = meta.get("fraud", {}) or {}
        self.fraud_score: float = fraud.get("score", 0.0)
        self.fraud_types: List[str] = fraud.get("types", []) or []
        self.is_tampered: bool = "tampered" in self.fraud_types
        self.is_screen: bool = "screen" in self.fraud_types

    @property
    def is_fraudulent(self) -> bool:
        """Return True if any fraud signal is present."""
        return self.is_tampered or self.is_screen or self.is_duplicate or self.fraud_score > 0.7

    @property
    def fraud_flags(self) -> List[str]:
        """Return a list of human-readable fraud flags."""
        flags = list(self.fraud_types)
        if self.is_duplicate:
            flags.append("duplicate_receipt")
        return flags

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "vendor_name": self.vendor_name,
            "vendor_address": self.vendor_address,
            "total": self.total,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "date": self.date,
            "currency_code": self.currency_code,
            "line_items": [i.to_dict() for i in self.line_items],
            "is_fraudulent": self.is_fraudulent,
            "fraud_score": self.fraud_score,
            "fraud_flags": self.fraud_flags,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class VeryfiError(Exception):
    """Raised when Veryfi API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _check_config() -> None:
    """Raise VeryfiError if required env vars are missing."""
    missing = []
    if not _client_id():
        missing.append("VERYFI_CLIENT_ID")
    if not _client_secret():
        missing.append("VERYFI_CLIENT_SECRET")
    if not _username():
        missing.append("VERYFI_USERNAME")
    if not _api_key():
        missing.append("VERYFI_API_KEY")
    if missing:
        raise VeryfiError(f"Missing Veryfi env vars: {', '.join(missing)}")


async def process_receipt_base64(
    image_base64: str,
    file_name: str = "receipt.jpg",
) -> VeryfiReceiptResult:
    """
    Send a base64-encoded receipt image to Veryfi for processing.

    Returns a VeryfiReceiptResult with line items and fraud indicators.
    Raises VeryfiError on any failure — NO fallback.
    """
    _check_config()

    url = _api_base_url().rstrip("/") + "/" + DOCUMENTS_ENDPOINT

    payload = {
        "file_data": image_base64,
        "file_name": file_name,
        "categories": ["Grocery"],
        "auto_delete": False,
    }
    payload_str = json.dumps(payload)
    headers = _build_headers(payload_str)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(url, content=payload_str, headers=headers)

        if resp.status_code == 200 or resp.status_code == 201:
            data = resp.json()
            result = VeryfiReceiptResult(data)
            logger.info(
                f"[Veryfi] Processed receipt: vendor={result.vendor_name}, "
                f"total={result.total}, items={len(result.line_items)}, "
                f"fraud_score={result.fraud_score}"
            )
            return result
        else:
            body = resp.text[:500]
            logger.error(f"[Veryfi] API error {resp.status_code}: {body}")
            raise VeryfiError(
                f"Veryfi API returned {resp.status_code}: {body}",
                status_code=resp.status_code,
            )

    except httpx.TimeoutException:
        logger.error("[Veryfi] Request timed out")
        raise VeryfiError("Veryfi request timed out")
    except httpx.RequestError as e:
        logger.error(f"[Veryfi] Request failed: {e}")
        raise VeryfiError(f"Veryfi request failed: {e}")


async def process_receipt_url(
    file_url: str,
) -> VeryfiReceiptResult:
    """
    Send a receipt image URL to Veryfi for processing.

    Returns a VeryfiReceiptResult with line items and fraud indicators.
    Raises VeryfiError on any failure — NO fallback.
    """
    _check_config()

    url = _api_base_url().rstrip("/") + "/" + DOCUMENTS_ENDPOINT

    payload = {
        "file_url": file_url,
        "categories": ["Grocery"],
        "auto_delete": False,
    }
    payload_str = json.dumps(payload)
    headers = _build_headers(payload_str)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(url, content=payload_str, headers=headers)

        if resp.status_code == 200 or resp.status_code == 201:
            data = resp.json()
            result = VeryfiReceiptResult(data)
            logger.info(
                f"[Veryfi] Processed receipt URL: vendor={result.vendor_name}, "
                f"total={result.total}, items={len(result.line_items)}"
            )
            return result
        else:
            body = resp.text[:500]
            logger.error(f"[Veryfi] API error {resp.status_code}: {body}")
            raise VeryfiError(
                f"Veryfi API returned {resp.status_code}: {body}",
                status_code=resp.status_code,
            )

    except httpx.TimeoutException:
        logger.error("[Veryfi] Request timed out")
        raise VeryfiError("Veryfi request timed out")
    except httpx.RequestError as e:
        logger.error(f"[Veryfi] Request failed: {e}")
        raise VeryfiError(f"Veryfi request failed: {e}")
