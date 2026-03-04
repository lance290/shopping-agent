"""Authentication helpers — verification (SMS/email), phone validation, allowlists."""
import logging
import os
import re
from typing import Optional

import httpx
import sqlalchemy as sa
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ModuleNotFoundError:  # pragma: no cover
    Client = None  # type: ignore
    TwilioRestException = Exception  # type: ignore

from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)


def _get_env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _get_from_email() -> str:
    return _get_env("FROM_EMAIL", "Agent Shopper <shopper@info.xcor-cto.com>")


ACCOUNT_EMAIL_TO_PHONE = {
    "kathleen@ecomedes.com": "+14152157928",
    "tconnors@gmail.com": "+16156796015",
}
ACCOUNT_PHONE_TO_EMAIL = {v: k for k, v in ACCOUNT_EMAIL_TO_PHONE.items()}

LOCKOUT_MINUTES = 45
MAX_ATTEMPTS = 5


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send verification code via Resend API. Returns True on success."""
    resend_api_key = _get_env("RESEND_API_KEY")
    if not resend_api_key:
        print(f"[AUTH] RESEND_API_KEY not set. Code would be sent to {to_email}")
        return True
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": _get_from_email(),
                    "to": [to_email],
                    "subject": "Your verification code",
                    "text": f"Your verification code is: {code}",
                },
            )
            if 200 <= response.status_code < 300:
                print(f"[AUTH] Email sent to {to_email}")
                return True
            else:
                print(f"[AUTH] Resend error: {response.status_code}")
                return False
    except httpx.TimeoutException:
        print(f"[AUTH] Resend timeout for {to_email}")
        return False
    except httpx.RequestError as e:
        print(f"[AUTH] Resend request error: {type(e).__name__}")
        return False


async def send_verification_sms(to_phone: str, code: str) -> bool:
    """Send verification code via Twilio API. Returns True on success."""
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("E2E_TEST_MODE") == "1":
        return True

    twilio_account_sid = _get_env("TWILIO_ACCOUNT_SID")
    twilio_auth_token = _get_env("TWILIO_AUTH_TOKEN")
    twilio_phone_number = _get_env("TWILIO_PHONE_NUMBER")
    twilio_verify_service_sid = _get_env("TWILIO_VERIFY_SERVICE_SID")

    if twilio_verify_service_sid and (not Client or not twilio_account_sid or not twilio_auth_token):
        print(
            "[AUTH] Twilio Verify configured but missing TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN or SDK."
        )
        return False

    if Client and twilio_account_sid and twilio_auth_token and twilio_verify_service_sid:
        try:
            client = Client(twilio_account_sid, twilio_auth_token)
            verification = client.verify.v2.services(twilio_verify_service_sid).verifications.create(
                to=to_phone,
                channel="sms",
            )
            print(f"[AUTH] Verify SMS started for {to_phone}: {verification.sid}")
            return True
        except TwilioRestException as e:
            print(f"[AUTH] Twilio Verify error: {e}")
            return False
        except Exception as e:
            print(f"[AUTH] Unexpected error starting Verify SMS: {e}")
            return False

    if not Client:
        print(f"[AUTH] Twilio SDK not installed. Code {code} would be sent to {to_phone}")
        return True

    if not twilio_account_sid or not twilio_auth_token or not twilio_phone_number:
        print(f"[AUTH] Twilio credentials not set. Code {code} would be sent to {to_phone}")
        return True

    try:
        client = Client(twilio_account_sid, twilio_auth_token)
        message = client.messages.create(
            body=f"Your Agent Shopper verification code is: {code}",
            from_=twilio_phone_number,
            to=to_phone
        )
        print(f"[AUTH] SMS sent to {to_phone}: {message.sid}")
        return True
    except TwilioRestException as e:
        print(f"[AUTH] Twilio error: {e}")
        return False
    except Exception as e:
        print(f"[AUTH] Unexpected error sending SMS: {e}")
        return False


def validate_phone_number(phone: str) -> str:
    """Basic phone number validation and normalization (E.164 format)."""
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone)
    
    # If it starts with 1 (USA country code) and is 11 digits, it's valid
    if len(cleaned) == 11 and cleaned.startswith('1'):
        return f"+{cleaned}"
    
    # If it is 10 digits, assume USA and prepend +1
    if len(cleaned) == 10:
        return f"+1{cleaned}"
        
    # TODO: Add better international support if needed
    raise ValueError("Invalid phone number format. Please use 10-digit US number or E.164 format.")


def _parse_csv_env(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value:
        return []
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return [item.strip() for item in value.split(',') if item.strip()]


def _get_allowed_phones() -> set[str]:
    out: set[str] = set()
    for p in _parse_csv_env(_get_env("ALLOWED_USER_PHONES")):
        try:
            out.add(validate_phone_number(p))
        except ValueError:
            continue
    return out


def _get_manager_phones() -> set[str]:
    out: set[str] = set()
    for p in _parse_csv_env(_get_env("MANAGER_USER_PHONES")):
        try:
            out.add(validate_phone_number(p))
        except ValueError:
            continue
    return out


def _is_allowed_identifier(email: Optional[str], phone: Optional[str]) -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True

    allowed_phones = _get_allowed_phones()
    manager_phones = _get_manager_phones()

    # Open to public: if no allowlist is configured, everyone is allowed
    if not allowed_phones:
        return True

    if phone:
        if phone in allowed_phones or phone in manager_phones:
            return True
    return False


def _is_manager_identifier(email: Optional[str], phone: Optional[str]) -> bool:
    manager_phones = _get_manager_phones()
    if phone and phone in manager_phones:
        return True
    return False


async def _reassign_user_foreign_keys(
    session: AsyncSession,
    primary_user_id: int,
    other_user_ids: list[int],
) -> None:
    if not other_user_ids:
        return

    tables_and_columns = [
        ("project", "user_id"),
        ("row", "user_id"),
        ("auth_session", "user_id"),
        ("clickout_event", "user_id"),
        ('"like"', "user_id"),
        ("comment", "user_id"),
        ("bug_report", "user_id"),
        ("share_link", "created_by"),
        ("deal_handoff", "buyer_user_id"),
    ]

    for table, col in tables_and_columns:
        stmt = sa.text(f"UPDATE {table} SET {col} = :primary WHERE {col} IN :others")
        stmt = stmt.bindparams(sa.bindparam("others", expanding=True))
        await session.exec(stmt, {"primary": primary_user_id, "others": other_user_ids})
