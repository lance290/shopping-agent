"""
FastAPI Application Example
Production-ready template with health checks and CORS
"""
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os
import httpx
from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sourcing import SourcingRepository, SearchResult
from database import init_db, get_session
from models import (
    Row, RowBase, RowCreate, RequestSpec,
    AuthLoginCode, AuthSession, Bid, Seller, User,
    hash_token, generate_verification_code, generate_session_token
)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Agent Shopper <shopper@info.xcor-cto.com>")


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

# Create FastAPI app
app = FastAPI(
    title="Shopping Agent Backend",
    description="Agent-facilitated competitive bidding backend",
    version="0.1.0"
)

# Initialize sourcing repository
sourcing_repo = SourcingRepository()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class HealthResponse(BaseModel):
    status: str
    version: str

class SearchRequest(BaseModel):
    query: str
    gl: Optional[str] = "us"
    hl: Optional[str] = "en"

class SearchResponse(BaseModel):
    results: List[SearchResult]

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0"
    }

# DB endpoints
@app.post("/rows", response_model=Row)
async def create_row(row: RowCreate, session: AsyncSession = Depends(get_session)):
    # Extract request_spec data
    request_spec_data = row.request_spec
    
    # Create Row
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency
    )
    session.add(db_row)
    await session.commit()
    await session.refresh(db_row)
    
    # Create RequestSpec linked to Row
    db_spec = RequestSpec(
        row_id=db_row.id,
        item_name=request_spec_data.item_name,
        constraints=request_spec_data.constraints,
        preferences=request_spec_data.preferences
    )
    session.add(db_spec)
    await session.commit()
    
    # Refresh row to ensure relationships are loaded (though we might need to eager load)
    await session.refresh(db_row)
    return db_row

@app.get("/rows", response_model=List[Row])
async def read_rows(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(Row))
    return result.all()

@app.get("/rows/{row_id}", response_model=Row)
async def read_row(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row

@app.delete("/rows/{row_id}")
async def delete_row(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Delete related RequestSpec first (foreign key constraint)
    result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    for spec in result.all():
        await session.delete(spec)
    
    # Delete related Bids
    from models import Bid
    result = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for bid in result.all():
        await session.delete(bid)
    
    await session.delete(row)
    await session.commit()
    return {"status": "deleted", "id": row_id}

class RowUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    budget_max: Optional[float] = None

@app.patch("/rows/{row_id}")
async def update_row(row_id: int, row_update: RowUpdate, session: AsyncSession = Depends(get_session)):
    print(f"Received PATCH request for row {row_id} with data: {row_update}")
    row = await session.get(Row, row_id)
    if not row:
        print(f"Row {row_id} not found")
        raise HTTPException(status_code=404, detail="Row not found")
    
    row_data = row_update.dict(exclude_unset=True)
    for key, value in row_data.items():
        setattr(row, key, value)
        
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    print(f"Row {row_id} updated successfully: {row}")
    return row

# Search endpoint
@app.post("/v1/sourcing/search", response_model=SearchResponse)
async def search_listings(request: SearchRequest):
    results = await sourcing_repo.search_all(request.query, gl=request.gl, hl=request.hl)
    return {"results": results}


# ============ AUTH ENDPOINTS ============

LOCKOUT_MINUTES = 45
MAX_ATTEMPTS = 5


class AuthStartRequest(BaseModel):
    email: EmailStr


class AuthStartResponse(BaseModel):
    status: str
    locked_until: Optional[datetime] = None


@app.post("/auth/start", response_model=AuthStartResponse)
async def auth_start(request: AuthStartRequest, session: AsyncSession = Depends(get_session)):
    """Send a verification code to the user's email."""
    email = request.email.lower()
    now = datetime.utcnow()
    
    # Check for existing active codes and lockout, then invalidate them
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
    
    # Generate new code
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
    
    # Send email
    await send_verification_email(email, code)
    
    return {"status": "sent"}


class AuthVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class AuthVerifyResponse(BaseModel):
    status: str
    session_token: Optional[str] = None


@app.post("/auth/verify", response_model=AuthVerifyResponse)
async def auth_verify(request: AuthVerifyRequest, session: AsyncSession = Depends(get_session)):
    """Verify the code and create a session."""
    email = request.email.lower()
    now = datetime.utcnow()
    
    # Find active code for this email
    result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.email == email, AuthLoginCode.is_active == True)
    )
    login_code = result.first()
    
    if not login_code:
        raise HTTPException(status_code=400, detail="No active code found. Request a new one.")
    
    # Check lockout
    if login_code.locked_until and login_code.locked_until > now:
        raise HTTPException(
            status_code=429,
            detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
        )
    
    # Verify code
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
    
    # Code is valid - deactivate it
    login_code.is_active = False
    session.add(login_code)
    
    # Create user if not exists (registration on first login)
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        user = User(email=email)
        session.add(user)
    
    # Create session
    token = generate_session_token()
    new_session = AuthSession(
        email=email,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()
    
    return {"status": "ok", "session_token": token}


class AuthMeResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None


async def get_current_session(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[AuthSession]:
    """Extract and validate session from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    token_hash = hash_token(token)
    
    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    return result.first()


@app.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Check if user is authenticated."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True, "email": auth_session.email}


@app.post("/auth/logout")
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


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("FastAPI application starting...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    await init_db()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
