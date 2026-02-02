"""Authentication routes - login, verify, session management."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
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
    AuthLoginCode, AuthSession, User,
    hash_token, generate_verification_code, generate_session_token
)
from audit import audit_log

router = APIRouter(tags=["auth"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Agent Shopper <shopper@info.xcor-cto.com>")

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID", "")

ALLOWED_USER_EMAILS = os.getenv("ALLOWED_USER_EMAILS", "")
ALLOWED_USER_PHONES = os.getenv("ALLOWED_USER_PHONES", "")
MANAGER_USER_EMAILS = os.getenv("MANAGER_USER_EMAILS", "")
MANAGER_USER_PHONES = os.getenv("MANAGER_USER_PHONES", "")

ACCOUNT_EMAIL_TO_PHONE = {
    "kathleen@ecomedes.com": "+14152157928",
    "tconnors@gmail.com": "+16156796015",
}
ACCOUNT_PHONE_TO_EMAIL = {v: k for k, v in ACCOUNT_EMAIL_TO_PHONE.items()}

LOCKOUT_MINUTES = 45
MAX_ATTEMPTS = 5


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send verification code via Resend API. Returns True on success."""
    if not RESEND_API_KEY:
        print(f"[AUTH] RESEND_API_KEY not set. Code would be sent to {to_email}")
        return True
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
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
    if Client and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
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

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        print(f"[AUTH] Twilio credentials not set. Code {code} would be sent to {to_phone}")
        return True

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your Agent Shopper verification code is: {code}",
            from_=TWILIO_PHONE_NUMBER,
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


def _get_allowed_emails() -> set[str]:
    return {e.lower() for e in _parse_csv_env(ALLOWED_USER_EMAILS)}


def _get_allowed_phones() -> set[str]:
    out: set[str] = set()
    for p in _parse_csv_env(ALLOWED_USER_PHONES):
        try:
            out.add(validate_phone_number(p))
        except ValueError:
            continue
    return out


def _get_manager_emails() -> set[str]:
    return {e.lower() for e in _parse_csv_env(MANAGER_USER_EMAILS)}


def _get_manager_phones() -> set[str]:
    out: set[str] = set()
    for p in _parse_csv_env(MANAGER_USER_PHONES):
        try:
            out.add(validate_phone_number(p))
        except ValueError:
            continue
    return out


def _is_allowed_identifier(email: Optional[str], phone: Optional[str]) -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True

    allowed_emails = _get_allowed_emails()
    allowed_phones = _get_allowed_phones()
    manager_emails = _get_manager_emails()
    manager_phones = _get_manager_phones()

    if email:
        if email in allowed_emails or email in manager_emails:
            return True
    if phone:
        if phone in allowed_phones or phone in manager_phones:
            return True
    return False


def _is_manager_identifier(email: Optional[str], phone: Optional[str]) -> bool:
    manager_emails = _get_manager_emails()
    manager_phones = _get_manager_phones()
    if email and email in manager_emails:
        return True
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
        ("share_search_event", "user_id"),
        ("deal_handoff", "buyer_user_id"),
    ]

    for table, col in tables_and_columns:
        stmt = sa.text(f"UPDATE {table} SET {col} = :primary WHERE {col} IN :others")
        stmt = stmt.bindparams(sa.bindparam("others", expanding=True))
        await session.exec(stmt, {"primary": primary_user_id, "others": other_user_ids})


async def get_current_session(
    authorization: Optional[str],
    session: AsyncSession
) -> Optional[AuthSession]:
    """Extract and validate session from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    
    # Try session token lookup
    token_hash = hash_token(token)
    
    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    return result.first()


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
    def validate_one_field(self):
        if not self.email and not self.phone:
            raise ValueError('Either email or phone must be provided')
        return self


class AuthStartResponse(BaseModel):

    status: str
    locked_until: Optional[datetime] = None


class AuthVerifyRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    code: str


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
    """Send a verification code to the user's email or phone."""
    email = auth_request.email.lower() if auth_request.email else None
    phone = auth_request.phone

    if phone:
        try:
            phone = validate_phone_number(phone)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not _is_allowed_identifier(email=email, phone=phone):
        raise HTTPException(status_code=403, detail="Not allowed")
    
    identifier = email or phone
    identifier_type = "email" if email else "phone"

    await audit_log(
        session=session,
        action="auth.login_start",
        details={"identifier": identifier, "type": identifier_type},
        request=req,
    )
    
    now = datetime.utcnow()
    
    # Check for existing active codes
    query = select(AuthLoginCode).where(AuthLoginCode.is_active == True)
    if email:
        query = query.where(AuthLoginCode.email == email)
    else:
        query = query.where(AuthLoginCode.phone_number == phone)
        
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
        email=email,
        phone_number=phone,
        code_hash=hash_token(code),
        is_active=True,
        attempt_count=0,
        locked_until=None,
    )
    session.add(new_login_code)
    await session.commit()
    
    sent = False
    if email:
        sent = await send_verification_email(email, code)
    elif phone:
        sent = await send_verification_sms(phone, code)
    
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send verification code")
        
    return {"status": "sent"}


@router.post("/auth/verify", response_model=AuthVerifyResponse)
async def auth_verify(request: AuthVerifyRequest, session: AsyncSession = Depends(get_session)):
    """Verify the code and create a session."""
    email = request.email.lower() if request.email else None
    phone = request.phone
    
    if phone:
        try:
            phone = validate_phone_number(phone)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    if not email and not phone:
         raise HTTPException(status_code=400, detail="Either email or phone must be provided")

    if not _is_allowed_identifier(email=email, phone=phone):
        raise HTTPException(status_code=403, detail="Not allowed")

    now = datetime.utcnow()
    
    query = select(AuthLoginCode).where(AuthLoginCode.is_active == True)
    if email:
        query = query.where(AuthLoginCode.email == email)
    else:
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
    if phone and Client and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
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
    else:
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
    if email:
        emails.add(email)
        mapped_phone = ACCOUNT_EMAIL_TO_PHONE.get(email)
        if mapped_phone:
            phones.add(mapped_phone)
    if phone:
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
        user = User(email=email, phone_number=phone)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    updated = False
    if email and not user.email:
        user.email = email
        updated = True
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

    if _is_manager_identifier(email=user.email, phone=user.phone_number) and not user.is_admin:
        user.is_admin = True
        updated = True

    if updated:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    token = generate_session_token()
    new_session = AuthSession(
        email=email,
        phone_number=phone,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()
    
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
