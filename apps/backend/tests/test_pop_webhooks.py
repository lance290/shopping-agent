"""Tests for Pop webhook handlers (Resend email + Twilio SMS)."""
import hashlib
import hmac
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, Bid
from routes.pop import _extract_twilio_media_urls, _extract_resend_image_urls


# ---------------------------------------------------------------------------
# Unit tests for media extraction helpers
# ---------------------------------------------------------------------------

def test_extract_twilio_media_urls_single_image():
    params = {
        "NumMedia": "1",
        "MediaUrl0": "https://example.com/photo.jpg",
        "MediaContentType0": "image/jpeg",
    }
    assert _extract_twilio_media_urls(params) == ["https://example.com/photo.jpg"]


def test_extract_twilio_media_urls_multiple_images():
    params = {
        "NumMedia": "3",
        "MediaUrl0": "https://example.com/a.jpg",
        "MediaContentType0": "image/jpeg",
        "MediaUrl1": "https://example.com/b.png",
        "MediaContentType1": "image/png",
        "MediaUrl2": "https://example.com/c.pdf",
        "MediaContentType2": "application/pdf",
    }
    result = _extract_twilio_media_urls(params)
    assert result == ["https://example.com/a.jpg", "https://example.com/b.png"]


def test_extract_twilio_media_urls_no_media():
    assert _extract_twilio_media_urls({"NumMedia": "0"}) == []
    assert _extract_twilio_media_urls({}) == []
    assert _extract_twilio_media_urls({"NumMedia": "abc"}) == []


def test_extract_twilio_media_urls_empty_url_skipped():
    params = {
        "NumMedia": "1",
        "MediaUrl0": "",
        "MediaContentType0": "image/jpeg",
    }
    assert _extract_twilio_media_urls(params) == []


def test_extract_resend_image_urls_single():
    payload = {
        "attachments": [
            {"content_type": "image/jpeg", "url": "https://example.com/fridge.jpg"}
        ]
    }
    assert _extract_resend_image_urls(payload) == ["https://example.com/fridge.jpg"]


def test_extract_resend_image_urls_multiple_mixed():
    payload = {
        "attachments": [
            {"content_type": "image/png", "url": "https://example.com/a.png"},
            {"content_type": "application/pdf", "url": "https://example.com/receipt.pdf"},
            {"content_type": "image/jpeg", "url": "https://example.com/b.jpg"},
        ]
    }
    result = _extract_resend_image_urls(payload)
    assert result == ["https://example.com/a.png", "https://example.com/b.jpg"]


def test_extract_resend_image_urls_no_attachments():
    assert _extract_resend_image_urls({}) == []
    assert _extract_resend_image_urls({"attachments": None}) == []
    assert _extract_resend_image_urls({"attachments": []}) == []


def test_extract_resend_image_urls_alternate_key_names():
    payload = {
        "attachments": [
            {"mime_type": "image/webp", "content_url": "https://example.com/pantry.webp"},
        ]
    }
    assert _extract_resend_image_urls(payload) == ["https://example.com/pantry.webp"]


def test_extract_resend_image_urls_malformed_attachment_skipped():
    payload = {
        "attachments": [
            "not a dict",
            {"content_type": "image/png", "url": "https://example.com/ok.png"},
        ]
    }
    assert _extract_resend_image_urls(payload) == ["https://example.com/ok.png"]


def test_extract_resend_image_urls_no_content_type_skipped():
    """Regression: attachments without content_type must NOT be treated as images."""
    payload = {
        "attachments": [
            {"url": "https://example.com/mystery.bin"},
            {"content_type": "image/png", "url": "https://example.com/ok.png"},
        ]
    }
    assert _extract_resend_image_urls(payload) == ["https://example.com/ok.png"]


# ---------------------------------------------------------------------------
# 12. POST /pop/webhooks/resend  (Resend inbound email)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resend_webhook_accepted(client: AsyncClient, pop_user):
    """Valid Resend webhook payload returns 200 accepted."""
    user, _ = pop_user
    payload = json.dumps({
        "from": f"Pop User <{user.email}>",
        "text": "I need milk and eggs",
        "subject": "Shopping list",
    }).encode()

    with patch("routes.pop._verify_resend_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_twilio_webhook_image_only_mms_dispatches(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """Image-only Twilio MMS should be accepted and forwarded with media URL."""
    user, _ = pop_user
    user.phone_number = "+15005550123"
    session.add(user)
    await session.commit()

    with patch("routes.pop._verify_twilio_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={
                    "From": "+15005550123",
                    "NumMedia": "1",
                    "MediaUrl0": "https://example.com/pantry.png",
                    "MediaContentType0": "image/png",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200
    args = mock_proc.call_args[0]
    assert args[0] == user.email
    assert "grocery photos" in args[1].lower()
    assert args[5] == ["https://example.com/pantry.png"]
    assert "application/xml" in resp.headers.get("content-type", "")
    assert "<Response/>" in resp.text


@pytest.mark.asyncio
async def test_resend_webhook_400_missing_sender(client: AsyncClient):
    """Resend webhook with missing 'from' field returns 400."""
    payload = json.dumps({"text": "I need milk", "subject": "test"}).encode()
    with patch("routes.pop._verify_resend_signature", return_value=True):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resend_webhook_400_missing_body(client: AsyncClient):
    """Resend webhook with missing 'text'/'html' fields returns 400."""
    payload = json.dumps({"from": "user@example.com", "subject": "test"}).encode()
    with patch("routes.pop._verify_resend_signature", return_value=True):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resend_webhook_401_invalid_signature(client: AsyncClient, pop_user):
    """Resend webhook with wrong HMAC signature returns 401."""
    user, _ = pop_user
    payload = json.dumps({
        "from": user.email,
        "text": "hello",
        "subject": "test",
    }).encode()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", "secret123"):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "resend-signature": "badhash",
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_resend_webhook_valid_signature_accepted(client: AsyncClient, pop_user):
    """Resend webhook with correct HMAC signature is accepted."""
    user, _ = pop_user
    secret = "my_webhook_secret"
    payload = json.dumps({
        "from": user.email,
        "text": "need bread",
        "subject": "shopping",
    }).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "resend-signature": sig,
                },
            )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_webhook_parses_full_name_email(client: AsyncClient, pop_user):
    """'From: Name <email>' format must be parsed to extract just the email."""
    user, _ = pop_user
    payload = json.dumps({
        "from": f"John Doe <{user.email}>",
        "text": "milk please",
        "subject": "list",
    }).encode()

    with patch("routes.pop._verify_resend_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    # process_pop_message should receive the parsed email, not "John Doe <email>"
    call_args = mock_proc.call_args
    assert call_args[0][0] == user.email


@pytest.mark.asyncio
async def test_resend_webhook_image_only_attachment_dispatches(client: AsyncClient, pop_user):
    """Image-only Resend payload should be accepted and forwarded with image URLs."""
    user, _ = pop_user
    payload = json.dumps({
        "from": user.email,
        "subject": "fridge photo",
        "attachments": [
            {"content_type": "image/jpeg", "url": "https://example.com/fridge.jpg"}
        ],
    }).encode()

    with patch("routes.pop._verify_resend_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    args = mock_proc.call_args[0]
    assert args[0] == user.email
    assert "grocery photos" in args[1].lower()
    assert args[5] == ["https://example.com/fridge.jpg"]


@pytest.mark.asyncio
async def test_resend_webhook_nested_data_envelope_parsed(client: AsyncClient, pop_user):
    """Resend webhook nested payload under data should be handled."""
    user, _ = pop_user
    payload = json.dumps({
        "type": "email.received",
        "data": {
            "from": f"User <{user.email}>",
            "text": "add bananas",
            "subject": "list",
        },
    }).encode()

    with patch("routes.pop._verify_resend_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    args = mock_proc.call_args[0]
    assert args[0] == user.email
    assert args[1] == "add bananas"


@pytest.mark.asyncio
async def test_resend_webhook_text_plus_image_dispatches(client: AsyncClient, pop_user):
    """Email with both text body and image attachment should forward both."""
    user, _ = pop_user
    payload = json.dumps({
        "from": user.email,
        "text": "Here is my fridge, what do I need?",
        "subject": "fridge photo",
        "attachments": [
            {"content_type": "image/jpeg", "url": "https://example.com/fridge.jpg"}
        ],
    }).encode()

    with patch("routes.pop._verify_resend_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    args = mock_proc.call_args[0]
    assert args[0] == user.email
    assert args[1] == "Here is my fridge, what do I need?"
    assert args[5] == ["https://example.com/fridge.jpg"]


@pytest.mark.asyncio
async def test_twilio_webhook_text_plus_image_dispatches(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """SMS with both text body and MMS image should forward both."""
    user, _ = pop_user
    user.phone_number = "+15005550777"
    session.add(user)
    await session.commit()

    with patch("routes.pop._verify_twilio_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={
                    "From": "+15005550777",
                    "Body": "what am I missing?",
                    "NumMedia": "1",
                    "MediaUrl0": "https://example.com/pantry.png",
                    "MediaContentType0": "image/png",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200
    args = mock_proc.call_args[0]
    assert args[0] == user.email
    assert args[1] == "what am I missing?"
    assert args[5] == ["https://example.com/pantry.png"]


# ---------------------------------------------------------------------------
# 13. POST /pop/webhooks/twilio  (Twilio inbound SMS)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_twilio_webhook_returns_twiml(client: AsyncClient, pop_user):
    """Valid Twilio webhook returns empty TwiML <Response/>."""
    user, _ = pop_user

    with patch("routes.pop._verify_twilio_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+15005550006", "Body": "need milk"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200
    assert "<Response/>" in resp.text
    assert "application/xml" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_twilio_webhook_400_missing_from(client: AsyncClient):
    """Twilio webhook without 'From' field returns 400."""
    with patch("routes.pop._verify_twilio_signature", return_value=True):
        resp = await client.post(
            "/pop/webhooks/twilio",
            data={"Body": "milk"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_twilio_webhook_400_missing_body(client: AsyncClient):
    """Twilio webhook without 'Body' field returns 400."""
    with patch("routes.pop._verify_twilio_signature", return_value=True):
        resp = await client.post(
            "/pop/webhooks/twilio",
            data={"From": "+15005550006"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_twilio_webhook_unknown_phone_sends_onboarding_sms(
    client: AsyncClient,
    session: AsyncSession,
):
    """Regression: unknown phone number triggers onboarding SMS (not NameError crash).

    Bug: send_pop_onboarding_sms was undefined — now correctly named send_pop_onboarding_sms.
    This test verifies the correct function is called without raising NameError.
    """
    with patch("routes.pop._verify_twilio_signature", return_value=True):
        with patch("routes.pop_notify.send_pop_onboarding_sms", return_value=True) as mock_sms:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+19999999999", "Body": "hello"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200, f"Should not crash on unknown phone, got {resp.status_code}: {resp.text}"
    mock_sms.assert_called_once_with("+19999999999")


@pytest.mark.asyncio
async def test_twilio_webhook_known_phone_dispatches_to_process_message(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """Known phone number dispatches to process_pop_message via background task."""
    user, _ = pop_user
    user.phone_number = "+15005550099"
    session.add(user)
    await session.commit()

    with patch("routes.pop._verify_twilio_signature", return_value=True):
        with patch("routes.pop_processor.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+15005550099", "Body": "add milk"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200


