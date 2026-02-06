"""Admin routes - audit logs, test endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func, text

from database import get_session
from models import (
    User, AuthSession, AuditLog, hash_token, generate_session_token,
    Row, Bid, ClickoutEvent, PurchaseEvent, Merchant,
    OutreachEvent, BugReport, SellerQuote,
)
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


@router.get("/admin/stats")
async def admin_stats(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get platform overview statistics (admin only)."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    async def _count(model, extra_filter=None):
        q = select(func.count(model.id))
        if extra_filter is not None:
            q = q.where(extra_filter)
        r = await session.exec(q)
        return r.one()

    total_users = await _count(User)
    users_7d = await _count(User, User.created_at >= week_ago)

    total_rows = await _count(Row)
    active_rows = await _count(Row, Row.status.notin_(["closed", "purchased", "archived"]))

    total_bids = await _count(Bid)

    total_clickouts = await _count(ClickoutEvent)
    clickouts_7d = await _count(ClickoutEvent, ClickoutEvent.created_at >= week_ago)

    total_purchases = await _count(PurchaseEvent)
    gmv_result = await session.exec(
        select(func.coalesce(func.sum(PurchaseEvent.amount), 0))
    )
    gmv = float(gmv_result.one())

    total_merchants = await _count(Merchant)

    total_outreach = await _count(OutreachEvent)
    outreach_quoted = await _count(SellerQuote)

    total_bugs = await _count(BugReport)
    open_bugs = await _count(BugReport, BugReport.status.in_(["captured", "issue_created", "fix_in_progress"]))

    return {
        "users": {"total": total_users, "last_7_days": users_7d},
        "rows": {"total": total_rows, "active": active_rows},
        "bids": {"total": total_bids},
        "clickouts": {"total": total_clickouts, "last_7_days": clickouts_7d},
        "purchases": {"total": total_purchases, "gmv": gmv},
        "merchants": {"total": total_merchants},
        "outreach": {"sent": total_outreach, "quoted": outreach_quoted},
        "bugs": {"total": total_bugs, "open": open_bugs},
    }


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
