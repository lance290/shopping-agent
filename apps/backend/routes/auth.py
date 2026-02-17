"""Authentication routes - login, verify, session management."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, EmailStr, validator, model_validator
from typing import Optional
from datetime import datetime, timedelta
import os
import httpx
import re
import sqlalchemy as sa
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ModuleNotFoundError:  # pragma: no cover
    Client = None  # type: ignore
    TwilioRestException = Exception  # type: ignore

from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import (
    AuthLoginCode, AuthSession, User, ShareLink,
    hash_token, generate_verification_code, generate_session_token
)
from dependencies import get_current_session

logger = logging.getLogger(__name__)
from audit import audit_log

router = APIRouter(tags=["auth"])


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


class AuthStartRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            try:
                return validate_phone_number(v)
            except ValueError as e:
                raise ValueError(str(e))
        return v
    
    @model_validator(mode='after')
    def validate_phone_only(self):
        return self


class AuthStartResponse(BaseModel):

    status: str
    locked_until: Optional[datetime] = None


class AuthVerifyRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    code: str
    referral_token: Optional[str] = None  # Viral Flywheel (PRD 06): share token that brought this user

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            try:
                return validate_phone_number(v)
            except ValueError as e:
                raise ValueError(str(e))
        return v

    @model_validator(mode='after')
    def validate_phone_only(self):
        return self


class AuthVerifyResponse(BaseModel):
    status: str
    session_token: Optional[str] = None
    user_id: Optional[int] = None


class AuthMeResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None
    phone_number: Optional[str] = None
    user_id: Optional[int] = None


class MintSessionRequest(BaseModel):
    email: EmailStr


class MintSessionResponse(BaseModel):
    session_token: str


# Rate limiting imports
from routes.rate_limit import check_rate_limit


@router.post("/auth/start", response_model=AuthStartResponse)
async def auth_start(
    auth_request: AuthStartRequest,
    req: Request,
    session: AsyncSession = Depends(get_session)
):
    """Send a verification code to the user's phone."""
    try:
        raw = await req.json()
    except Exception:
        raw = {}
    if isinstance(raw, dict) and raw.get("email"):
        raise HTTPException(status_code=400, detail="Email login is disabled. Use phone number instead.")

    phone = auth_request.phone
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    try:
        phone = validate_phone_number(phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not _is_allowed_identifier(email=None, phone=phone):
        raise HTTPException(status_code=403, detail="Not allowed")
    
    identifier = phone
    identifier_type = "phone"

    await audit_log(
        session=session,
        action="auth.login_start",
        details={"identifier": identifier, "type": identifier_type},
        request=req,
    )
    
    now = datetime.utcnow()
    
    # Check for existing active codes
    query = (
        select(AuthLoginCode)
        .where(AuthLoginCode.is_active == True)
        .where(AuthLoginCode.phone_number == phone)
    )
        
    result = await session.exec(query)
    existing_codes = result.all()
    
    for existing_code in existing_codes:
        if existing_code.locked_until and existing_code.locked_until > now:
            raise HTTPException(
                status_code=429,
                detail={"status": "locked", "locked_until": existing_code.locked_until.isoformat()}
            )
        existing_code.is_active = False
        session.add(existing_code)
    
    code = generate_verification_code()
    new_login_code = AuthLoginCode(
        email=None,
        phone_number=phone,
        code_hash=hash_token(code),
        is_active=True,
        attempt_count=0,
        locked_until=None,
    )
    session.add(new_login_code)
    await session.commit()
    
    # If dev bypass code is configured, skip Twilio entirely — code stored, user verifies with bypass
    dev_bypass = _get_env("DEV_BYPASS_CODE")
    if dev_bypass:
        print(f"[AUTH] DEV MODE: Skipping SMS for {phone}, use bypass code")
        return {"status": "sent"}

    sent = await send_verification_sms(phone, code)
    
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send verification code")
        
    return {"status": "sent"}


@router.post("/auth/verify", response_model=AuthVerifyResponse)
async def auth_verify(
    request: AuthVerifyRequest,
    req: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Verify the code and create a session."""
    try:
        raw = await req.json()
    except Exception:
        raw = {}
    if isinstance(raw, dict) and raw.get("email"):
        raise HTTPException(status_code=400, detail="Email login is disabled. Use phone number instead.")

    phone = request.phone
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    try:
        phone = validate_phone_number(phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not _is_allowed_identifier(email=None, phone=phone):
        raise HTTPException(status_code=403, detail="Not allowed")

    now = datetime.utcnow()
    
    query = select(AuthLoginCode).where(AuthLoginCode.is_active == True)
    query = query.where(AuthLoginCode.phone_number == phone)
        
    result = await session.exec(query)
    login_code = result.first()
    
    if not login_code:
        raise HTTPException(status_code=400, detail="No active code found. Request a new one.")
    
    if login_code.locked_until and login_code.locked_until > now:
        raise HTTPException(
            status_code=429,
            detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
        )
    
    is_valid = False
    skip_twilio = os.getenv("PYTEST_CURRENT_TEST") or os.getenv("E2E_TEST_MODE") == "1"

    # Dev bypass: accept DEV_BYPASS_CODE without Twilio
    dev_bypass = _get_env("DEV_BYPASS_CODE")
    if dev_bypass and request.code == dev_bypass:
        is_valid = True
        skip_twilio = True
        print(f"[AUTH] DEV MODE: Bypass code accepted for {phone}")

    twilio_account_sid = _get_env("TWILIO_ACCOUNT_SID")
    twilio_auth_token = _get_env("TWILIO_AUTH_TOKEN")
    twilio_verify_service_sid = _get_env("TWILIO_VERIFY_SERVICE_SID")

    if not skip_twilio and not is_valid and phone and Client and twilio_account_sid and twilio_auth_token and twilio_verify_service_sid:
        try:
            client = Client(twilio_account_sid, twilio_auth_token)
            check = client.verify.v2.services(twilio_verify_service_sid).verification_checks.create(
                to=phone,
                code=request.code,
            )
            is_valid = check.status == "approved"
        except TwilioRestException as e:
            print(f"[AUTH] Twilio Verify check error: {e}")
            is_valid = False
        except Exception as e:
            print(f"[AUTH] Unexpected error checking Verify code: {e}")
            is_valid = False
    elif not is_valid:
        is_valid = hash_token(request.code) == login_code.code_hash

    if not is_valid:
        login_code.attempt_count += 1
        if login_code.attempt_count >= MAX_ATTEMPTS:
            login_code.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            login_code.is_active = False
        session.add(login_code)
        await session.commit()
        
        remaining = MAX_ATTEMPTS - login_code.attempt_count
        if remaining <= 0:
            raise HTTPException(
                status_code=429,
                detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
            )
        raise HTTPException(status_code=400, detail=f"Invalid code. {remaining} attempts remaining.")
    
    login_code.is_active = False
    session.add(login_code)
    
    # Find or create user
    emails: set[str] = set()
    phones: set[str] = set()
    phones.add(phone)
    mapped_email = ACCOUNT_PHONE_TO_EMAIL.get(phone)
    if mapped_email:
        emails.add(mapped_email)

    conds = []
    for e in emails:
        conds.append(User.email == e)
    for p in phones:
        conds.append(User.phone_number == p)

    matching_users: list[User] = []
    if conds:
        result = await session.exec(select(User).where(or_(*conds)))
        matching_users = result.all()

    user: Optional[User] = None
    if matching_users:
        user = sorted(matching_users, key=lambda u: u.id or 0)[0]

        if len(matching_users) > 1:
            primary_id = user.id
            other_ids = [u.id for u in matching_users[1:] if u.id is not None]

            if primary_id is not None and other_ids:
                await _reassign_user_foreign_keys(session, primary_id, other_ids)

                for other in matching_users[1:]:
                    other.email = None
                    other.phone_number = None
                    other.is_admin = False
                    session.add(other)

                await session.commit()

    if not user:
        # Viral Flywheel (PRD 06): capture referral attribution on signup
        referral_share_token = request.referral_token
        signup_source = "share" if referral_share_token else "direct"

        user = User(
            email=next(iter(emails), None),
            phone_number=phone,
            referral_share_token=referral_share_token,
            signup_source=signup_source,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # If referred, increment ShareLink.signup_conversion_count and notify referrer
        if referral_share_token:
            try:
                share_result = await session.exec(
                    select(ShareLink).where(ShareLink.token == referral_share_token)
                )
                share_link = share_result.first()
                if share_link:
                    share_link.signup_conversion_count = (share_link.signup_conversion_count or 0) + 1
                    session.add(share_link)

                    # Notify the referrer
                    if share_link.created_by:
                        from routes.notifications import create_notification
                        await create_notification(
                            session,
                            user_id=share_link.created_by,
                            type="referral",
                            title="Someone you shared with just joined!",
                            body=f"A new user signed up via your share link.",
                            resource_type="user",
                            resource_id=user.id,
                        )

                    await session.commit()
            except Exception as e:
                logger.warning(f"Referral attribution error (non-fatal): {e}")

    updated = False
    if phone and not user.phone_number:
        user.phone_number = phone
        updated = True
    for e in emails:
        if e and not user.email:
            user.email = e
            updated = True
    for p in phones:
        if p and not user.phone_number:
            user.phone_number = p
            updated = True

    if _is_manager_identifier(email=None, phone=user.phone_number) and not user.is_admin:
        user.is_admin = True
        updated = True

    if updated:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    token = generate_session_token()
    new_session = AuthSession(
        email=user.email,
        phone_number=phone,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()

    # Set secure session cookie (PRD-03a: Session Cookie Security Configuration)
    # Detect production environment
    is_production = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production"

    # Set cookie with security attributes
    response.set_cookie(
        key="sa_session",
        value=token,
        httponly=True,           # Prevent XSS access
        samesite="strict",       # Prevent CSRF attacks
        secure=is_production,    # HTTPS-only in production
        path="/",                # Available to all routes
        max_age=604800,          # 7 days (matching session expiration)
    )

    return {"status": "ok", "session_token": token, "user_id": user.id}


@router.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Check if user is authenticated."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # If we have a user_id, get the latest user details (in case phone/email changed)
    phone_number = auth_session.phone_number
    email = auth_session.email
    
    if auth_session.user_id:
         user = await session.get(User, auth_session.user_id)
         if user:
             phone_number = user.phone_number
             email = user.email

    return {
        "authenticated": True, 
        "email": email,
        "phone_number": phone_number,
        "user_id": auth_session.user_id
    }


@router.post("/auth/logout")
async def auth_logout(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Revoke the current session."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_session.revoked_at = datetime.utcnow()
    session.add(auth_session)
    await session.commit()
    
    return {"status": "ok"}
