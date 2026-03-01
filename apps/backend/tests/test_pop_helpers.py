"""Unit tests for Pop helper functions and notify utilities."""
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

# ---------------------------------------------------------------------------
# 14. Helper function unit tests
# ---------------------------------------------------------------------------

def test_load_chat_history_empty_row():
    """_load_chat_history returns [] for a row with no chat_history."""
    from routes.pop_helpers import _load_chat_history
    row = MagicMock()
    row.chat_history = None
    assert _load_chat_history(row) == []


def test_load_chat_history_valid_json():
    """_load_chat_history correctly parses stored JSON."""
    from routes.pop_helpers import _load_chat_history
    history = [
        {"role": "user", "content": "I need eggs"},
        {"role": "assistant", "content": "Added eggs!"},
    ]
    row = MagicMock()
    row.chat_history = json.dumps(history)
    result = _load_chat_history(row)
    assert len(result) == 2
    assert result[0]["role"] == "user"


def test_load_chat_history_invalid_json_returns_empty():
    """_load_chat_history returns [] for corrupt JSON (no crash)."""
    from routes.pop_helpers import _load_chat_history
    row = MagicMock()
    row.chat_history = "{broken json["
    assert _load_chat_history(row) == []


def test_load_chat_history_truncates_at_50_entries():
    """_load_chat_history returns list as-is (truncation is in _append, not _load)."""
    from routes.pop_helpers import _load_chat_history
    history = [{"role": "user", "content": f"msg {i}"} for i in range(60)]
    row = MagicMock()
    row.chat_history = json.dumps(history)
    result = _load_chat_history(row)
    assert len(result) == 60  # _load does not truncate, _append does


@pytest.mark.asyncio
async def test_append_chat_history_persists_exchange(session: AsyncSession, pop_user, pop_row: Row):
    """_append_chat_history stores user + assistant messages on the row."""
    from routes.pop_helpers import _append_chat_history

    await _append_chat_history(session, pop_row, "I need eggs", "Added eggs to your list!")

    await session.refresh(pop_row)
    history = json.loads(pop_row.chat_history)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "I need eggs"}
    assert history[1] == {"role": "assistant", "content": "Added eggs to your list!"}


@pytest.mark.asyncio
async def test_append_chat_history_truncates_at_50(session: AsyncSession, pop_user, pop_row: Row):
    """_append_chat_history caps history at 50 messages to prevent unbounded growth."""
    from routes.pop_helpers import _append_chat_history

    # Pre-load 48 messages
    initial = [{"role": "user", "content": f"msg {i}"} for i in range(48)]
    pop_row.chat_history = json.dumps(initial)
    session.add(pop_row)
    await session.commit()

    # This append adds 2 more = 50 — should stay at 50
    await _append_chat_history(session, pop_row, "msg 48", "reply 48")
    await session.refresh(pop_row)
    assert len(json.loads(pop_row.chat_history)) == 50

    # One more append = 52 → truncate to 50
    await _append_chat_history(session, pop_row, "msg 49", "reply 49")
    await session.refresh(pop_row)
    assert len(json.loads(pop_row.chat_history)) == 50


@pytest.mark.asyncio
async def test_ensure_project_member_creates_member(
    session: AsyncSession, pop_user, pop_project: Project
):
    """_ensure_project_member creates a ProjectMember if one doesn't exist."""
    from routes.pop_helpers import _ensure_project_member
    user, _ = pop_user

    member = await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    assert member.project_id == pop_project.id
    assert member.user_id == user.id
    assert member.channel == "web"


@pytest.mark.asyncio
async def test_ensure_project_member_is_idempotent(
    session: AsyncSession, pop_user, pop_project: Project
):
    """Calling _ensure_project_member twice for the same user does not duplicate records."""
    from routes.pop_helpers import _ensure_project_member
    from sqlmodel import select

    user, _ = pop_user
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == pop_project.id,
        ProjectMember.user_id == user.id,
    )
    result = await session.execute(stmt)
    members = result.scalars().all()
    assert len(members) == 1, "Idempotent — must not create duplicate ProjectMember"


@pytest.mark.asyncio
async def test_ensure_project_member_updates_channel(
    session: AsyncSession, pop_user, pop_project: Project
):
    """_ensure_project_member updates channel if it changes."""
    from routes.pop_helpers import _ensure_project_member
    user, _ = pop_user

    await _ensure_project_member(session, pop_project.id, user.id, channel="email")
    member = await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    assert member.channel == "web"


def test_verify_resend_signature_passes_with_correct_hmac():
    """_verify_resend_signature accepts a correctly signed payload."""
    from routes.pop import _verify_resend_signature
    secret = "test_secret_abc"
    payload = b'{"from": "user@example.com", "text": "milk"}'
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        assert _verify_resend_signature(payload, sig) is True


def test_verify_resend_signature_rejects_tampered_payload():
    """_verify_resend_signature rejects payload that doesn't match signature."""
    from routes.pop import _verify_resend_signature
    secret = "test_secret_abc"
    original = b'{"from": "user@example.com", "text": "milk"}'
    sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
    tampered = b'{"from": "attacker@evil.com", "text": "milk"}'

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        assert _verify_resend_signature(tampered, sig) is False


def test_verify_resend_signature_rejects_when_no_secret():
    """_verify_resend_signature returns False (fail-closed) when no secret configured."""
    from routes.pop import _verify_resend_signature
    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):
        assert _verify_resend_signature(b"payload", "anysig") is False


# ---------------------------------------------------------------------------
# 15. send_pop_reply / send_pop_sms demo mode tests (no real credentials)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_bob_reply_demo_mode_returns_success():
    """send_pop_reply in demo mode (no RESEND_API_KEY) returns success without crashing."""
    from routes.pop_notify import send_pop_reply
    with patch("routes.pop_notify.RESEND_API_KEY", ""):
        result = await send_pop_reply(
            "test@example.com",
            "Test subject",
            "Hello from Pop!",
        )
    assert result.success is True
    assert result.message_id == "demo-pop-reply"


def test_send_bob_sms_demo_mode_returns_true():
    """send_pop_sms in demo mode (no Twilio creds) returns True without crashing."""
    from routes.pop_notify import send_pop_sms
    with patch("routes.pop_notify.TWILIO_ACCOUNT_SID", ""):
        result = send_pop_sms("+15005550006", "Hello!")
    assert result is True


# ---------------------------------------------------------------------------
# 16. process_pop_message edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_pop_message_unknown_user_sends_onboarding(
    session: AsyncSession,
):
    """process_pop_message for an unknown email sends onboarding email (no crash)."""
    from routes.pop_processor import process_pop_message

    with patch("routes.pop_processor.send_pop_onboarding_email", new_callable=AsyncMock) as mock_email:
        await process_pop_message(
            "unknown@nowhere.com",
            "I need groceries",
            session,
            channel="email",
        )
    mock_email.assert_called_once_with("unknown@nowhere.com")


@pytest.mark.asyncio
async def test_process_pop_message_unknown_sms_sends_onboarding_sms(
    session: AsyncSession,
):
    """process_pop_message via SMS for unknown user sends onboarding SMS."""
    from routes.pop_processor import process_pop_message

    with patch("routes.pop_processor.send_pop_onboarding_sms", return_value=True) as mock_sms:
        await process_pop_message(
            "unknown@nowhere.com",
            "need milk",
            session,
            channel="sms",
            sender_phone="+19998887777",
        )
    mock_sms.assert_called_once_with("+19998887777")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _empty_async_gen():
    """Empty async generator for mocking _stream_search."""
    return
    yield  # makes it an async generator
