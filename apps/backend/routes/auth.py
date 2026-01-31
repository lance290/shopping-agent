"""Authentication routes - login, verify, session management."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import os
import httpx

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import (
    AuthLoginCode, AuthSession, User,
    hash_token, generate_verification_code, generate_session_token
)
from audit import audit_log
from clerk_auth import get_clerk_user_id

router = APIRouter(tags=["auth"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Agent Shopper <shopper@info.xcor-cto.com>")
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


async def get_current_session(
    authorization: Optional[str],
    session: AsyncSession
) -> Optional[AuthSession]:
    """Extract and validate session from Authorization header.
    
    Supports both legacy session tokens and Clerk JWTs.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    
    # Debug: log token info
    token_parts = token.split('.') if token else []
    print(f"[AUTH DEBUG] Token length: {len(token)}, parts: {len(token_parts)}, first 50 chars: {token[:50] if token else 'empty'}")
    
    # First, try Clerk JWT verification
    clerk_user_id = get_clerk_user_id(token)
    if clerk_user_id:
        result = await session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.first()
        
        if not user:
            user = User(clerk_user_id=clerk_user_id, email=None)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"[CLERK] Created new user {user.id} for Clerk ID {clerk_user_id}")
        
        fake_session = AuthSession(
            user_id=user.id,
            session_token_hash="clerk_jwt",
            email=user.email,
        )
        fake_session.id = -1
        return fake_session
    
    # Fallback: try legacy session token lookup
    token_hash = hash_token(token)
    
    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    return result.first()


class AuthStartRequest(BaseModel):
    email: EmailStr


class AuthStartResponse(BaseModel):
    status: str
    locked_until: Optional[datetime] = None


class AuthVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class AuthVerifyResponse(BaseModel):
    status: str
    session_token: Optional[str] = None


class AuthMeResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None


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
    """Send a verification code to the user's email."""
    email = auth_request.email.lower()
    
    await audit_log(
        session=session,
        action="auth.login_start",
        details={"email": email},
        request=req,
    )
    
    now = datetime.utcnow()
    
    result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.email == email, AuthLoginCode.is_active == True)
    )
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
        code_hash=hash_token(code),
        is_active=True,
        attempt_count=0,
        locked_until=None,
    )
    session.add(new_login_code)
    await session.commit()
    
    await send_verification_email(email, code)
    
    return {"status": "sent"}


@router.post("/auth/verify", response_model=AuthVerifyResponse)
async def auth_verify(request: AuthVerifyRequest, session: AsyncSession = Depends(get_session)):
    """Verify the code and create a session."""
    email = request.email.lower()
    now = datetime.utcnow()
    
    result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.email == email, AuthLoginCode.is_active == True)
    )
    login_code = result.first()
    
    if not login_code:
        raise HTTPException(status_code=400, detail="No active code found. Request a new one.")
    
    if login_code.locked_until and login_code.locked_until > now:
        raise HTTPException(
            status_code=429,
            detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
        )
    
    if hash_token(request.code) != login_code.code_hash:
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
    
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    token = generate_session_token()
    new_session = AuthSession(
        email=email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()
    
    return {"status": "ok", "session_token": token}


@router.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Check if user is authenticated."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True, "email": auth_session.email}


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
