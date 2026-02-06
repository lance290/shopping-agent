"""Admin routes - audit logs, test endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text

from database import get_session
from models import User, AuthSession, AuditLog, hash_token, generate_session_token
from dependencies import require_admin
from routes.rate_limit import check_rate_limit

router = APIRouter(tags=["admin"])


class MintSessionRequest(BaseModel):
    phone: str


class MintSessionResponse(BaseModel):
    session_token: str


@router.post("/test/mint-session", response_model=MintSessionResponse)
async def mint_session(request: MintSessionRequest, session: AsyncSession = Depends(get_session)):
    """
    Test-only endpoint to mint a session without email interaction.
    Only enabled when E2E_TEST_MODE=1 env var is set.
    """
    if os.getenv("E2E_TEST_MODE") != "1":
        raise HTTPException(status_code=404, detail="Not Found")
    
    from routes.auth import validate_phone_number

    phone = validate_phone_number(request.phone)

    if not check_rate_limit(f"mint:{phone}", "auth_start"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(select(User).where(User.phone_number == phone))
    user = result.first()
    if not user:
        user = User(phone_number=phone)
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
    
    return {"session_token": token}


@router.post("/test/reset-db")
async def test_reset_db(session: AsyncSession = Depends(get_session)):
    if os.getenv("E2E_TEST_MODE") != "1":
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        await session.execute(
            text(
                'TRUNCATE TABLE comment, "like", bid, request_spec, "row", project, clickout_event, bug_report, audit_log, auth_login_code, auth_session, "user" RESTART IDENTITY CASCADE;'
            )
        )
        await session.commit()
        return {"status": "ok"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"DB reset failed: {str(e)}")


@router.get("/admin/audit")
async def list_audit_logs(
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List audit logs (admin only)."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if since:
        query = query.where(AuditLog.timestamp >= since)
    
    result = await session.exec(query)
    return result.all()
