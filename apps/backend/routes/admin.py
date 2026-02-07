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
    OutreachEvent, BugReport, SellerQuote, ShareLink,
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

    # Revenue tracking (Phase 4)
    revenue_result = await session.exec(
        select(func.coalesce(func.sum(PurchaseEvent.platform_fee_amount), 0))
    )
    total_platform_revenue = float(revenue_result.one())

    affiliate_clicks = await _count(
        ClickoutEvent,
        ClickoutEvent.affiliate_tag.isnot(None)
    )

    return {
        "users": {"total": total_users, "last_7_days": users_7d},
        "rows": {"total": total_rows, "active": active_rows},
        "bids": {"total": total_bids},
        "clickouts": {"total": total_clickouts, "last_7_days": clickouts_7d, "with_affiliate_tag": affiliate_clicks},
        "purchases": {"total": total_purchases, "gmv": gmv},
        "revenue": {"platform_total": total_platform_revenue},
        "merchants": {"total": total_merchants},
        "outreach": {"sent": total_outreach, "quoted": outreach_quoted},
        "bugs": {"total": total_bugs, "open": open_bugs},
    }


@router.get("/admin/revenue")
async def admin_revenue(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed revenue breakdown by stream (admin only)."""
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    # Revenue by type
    revenue_by_type = await session.exec(
        select(
            PurchaseEvent.revenue_type,
            func.count(PurchaseEvent.id),
            func.coalesce(func.sum(PurchaseEvent.amount), 0),
            func.coalesce(func.sum(PurchaseEvent.platform_fee_amount), 0),
        ).group_by(PurchaseEvent.revenue_type)
    )
    streams = {}
    for row in revenue_by_type.all():
        rtype, count, total_amount, platform_fee = row
        streams[rtype] = {
            "count": count,
            "total_amount": float(total_amount),
            "platform_revenue": float(platform_fee),
        }

    # Clickout stats (affiliate performance)
    total_clickouts_result = await session.exec(
        select(func.count(ClickoutEvent.id))
    )
    total_clickouts = total_clickouts_result.one()

    affiliate_clickouts_result = await session.exec(
        select(func.count(ClickoutEvent.id)).where(
            ClickoutEvent.affiliate_tag.isnot(None)
        )
    )
    affiliate_clickouts = affiliate_clickouts_result.one()

    clickouts_7d_result = await session.exec(
        select(func.count(ClickoutEvent.id)).where(
            ClickoutEvent.created_at >= week_ago
        )
    )
    clickouts_7d = clickouts_7d_result.one()

    # Merchant Stripe Connect status
    connected_merchants_result = await session.exec(
        select(func.count(Merchant.id)).where(
            Merchant.stripe_onboarding_complete == True
        )
    )
    connected_merchants = connected_merchants_result.one()

    total_merchants_result = await session.exec(
        select(func.count(Merchant.id))
    )
    total_merchants = total_merchants_result.one()

    return {
        "period": {"from": month_ago.isoformat(), "to": now.isoformat()},
        "streams": streams,
        "clickouts": {
            "total": total_clickouts,
            "with_affiliate_tag": affiliate_clickouts,
            "last_7_days": clickouts_7d,
            "affiliate_rate": round(affiliate_clickouts / max(total_clickouts, 1), 3),
        },
        "stripe_connect": {
            "connected_merchants": connected_merchants,
            "total_merchants": total_merchants,
        },
    }


@router.get("/admin/growth")
async def growth_metrics(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Viral Growth Flywheel metrics (PRD 06).
    Returns K-factor, referral graph, seller-to-buyer conversion, collaborator funnel.
    """
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)

    # ── K-Factor Calculation ──
    # K = avg(invitations_per_user) × avg(conversion_rate_per_invitation)

    # Total users who created at least one share link
    sharers_result = await session.exec(
        select(func.count(func.distinct(ShareLink.created_by)))
        .where(ShareLink.created_by.isnot(None))
    )
    total_sharers = sharers_result.one() or 0

    # Total share links created
    total_shares_result = await session.exec(
        select(func.count(ShareLink.id))
    )
    total_shares = total_shares_result.one() or 0

    # Total signups attributed to share links
    total_referral_signups_result = await session.exec(
        select(func.count(User.id))
        .where(User.referral_share_token.isnot(None))
    )
    total_referral_signups = total_referral_signups_result.one() or 0

    # Total share link clicks
    total_clicks_result = await session.exec(
        select(func.coalesce(func.sum(ShareLink.click_count), 0))
    )
    total_clicks = total_clicks_result.one() or 0

    # K-factor
    avg_shares_per_user = total_shares / max(total_sharers, 1)
    conversion_rate = total_referral_signups / max(total_clicks, 1)
    k_factor = round(avg_shares_per_user * conversion_rate, 4)

    # ── Referral Graph (top referrers) ──
    referral_graph_query = (
        select(
            ShareLink.created_by,
            func.count(ShareLink.id).label("shares_created"),
            func.coalesce(func.sum(ShareLink.signup_conversion_count), 0).label("signups_driven"),
            func.coalesce(func.sum(ShareLink.click_count), 0).label("total_clicks"),
        )
        .where(ShareLink.created_by.isnot(None))
        .group_by(ShareLink.created_by)
        .order_by(func.coalesce(func.sum(ShareLink.signup_conversion_count), 0).desc())
        .limit(25)
    )
    referral_graph_result = await session.exec(referral_graph_query)
    referral_rows = referral_graph_result.all()

    # Fetch user details for referrers
    referrer_ids = [r[0] for r in referral_rows if r[0]]
    referrer_details = {}
    if referrer_ids:
        users_result = await session.exec(
            select(User.id, User.email, User.phone_number)
            .where(User.id.in_(referrer_ids))
        )
        for uid, email, phone in users_result:
            referrer_details[uid] = {"email": email, "phone": phone}

    referral_graph = [
        {
            "user_id": row[0],
            "email": referrer_details.get(row[0], {}).get("email"),
            "shares_created": row[1],
            "signups_driven": row[2],
            "total_clicks": row[3],
        }
        for row in referral_rows
    ]

    # ── Seller-to-Buyer Conversion ──
    # Users who are both merchants AND have created rows (they buy + sell)
    merchant_user_ids_result = await session.exec(
        select(Merchant.user_id).where(Merchant.user_id.isnot(None))
    )
    merchant_user_ids = [uid for uid in merchant_user_ids_result]

    sellers_who_buy = 0
    if merchant_user_ids:
        sellers_who_buy_result = await session.exec(
            select(func.count(func.distinct(Row.user_id)))
            .where(Row.user_id.in_(merchant_user_ids))
        )
        sellers_who_buy = sellers_who_buy_result.one() or 0

    total_merchants_result = await session.exec(select(func.count(Merchant.id)))
    total_merchants = total_merchants_result.one() or 0

    seller_to_buyer_rate = round(sellers_who_buy / max(total_merchants, 1), 4)

    # ── Collaborator-to-Buyer Funnel ──
    # Stage 1: Share link clicks (total_clicks computed above)
    # Stage 2: Referral signups (total_referral_signups computed above)
    # Stage 3: Referred users who created their own row
    referred_buyers_result = await session.exec(
        select(func.count(func.distinct(Row.user_id)))
        .where(
            Row.user_id.in_(
                select(User.id).where(User.referral_share_token.isnot(None))
            )
        )
    )
    referred_buyers = referred_buyers_result.one() or 0

    # ── Total users (for context) ──
    total_users_result = await session.exec(select(func.count(User.id)))
    total_users = total_users_result.one() or 0

    return {
        "period": {"from": month_ago.isoformat(), "to": now.isoformat()},
        "k_factor": {
            "value": k_factor,
            "target": 1.2,
            "components": {
                "avg_shares_per_user": round(avg_shares_per_user, 2),
                "click_to_signup_conversion": round(conversion_rate, 4),
                "total_sharers": total_sharers,
                "total_shares": total_shares,
                "total_clicks": total_clicks,
                "total_referral_signups": total_referral_signups,
            },
        },
        "referral_graph": referral_graph,
        "seller_to_buyer": {
            "total_merchants": total_merchants,
            "sellers_who_also_buy": sellers_who_buy,
            "conversion_rate": seller_to_buyer_rate,
        },
        "collaborator_funnel": {
            "share_clicks": total_clicks,
            "referral_signups": total_referral_signups,
            "referred_who_created_rows": referred_buyers,
            "click_to_signup_rate": round(total_referral_signups / max(total_clicks, 1), 4),
            "signup_to_buyer_rate": round(referred_buyers / max(total_referral_signups, 1), 4),
        },
        "total_users": total_users,
    }


@router.get("/admin/metrics")
async def admin_metrics(
    days: int = 30,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Core success metrics (PRD 09):
    M1: Avg time to first usable options per row
    M2: Offer click-through rate (CTR)
    M3: Clickout success rate (no broken redirects)
    M4: Affiliate handler coverage
    M5: Revenue per active user
    Plus expanded metrics M6-M10.
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # M1: Avg time from row creation to first bid
    m1_result = await session.execute(
        text(
            "SELECT AVG(EXTRACT(EPOCH FROM (first_bid.created_at - r.created_at))) "
            "FROM row r "
            "JOIN LATERAL ( "
            "  SELECT created_at FROM bid WHERE bid.row_id = r.id ORDER BY created_at LIMIT 1 "
            ") first_bid ON true "
            "WHERE r.created_at >= :period_start"
        ),
        {"period_start": period_start},
    )
    avg_time_to_first_result_seconds = m1_result.scalar() or 0

    # M2: Offer CTR (clickouts / bids shown)
    total_bids_result = await session.exec(
        select(func.count(Bid.id)).where(Bid.created_at >= period_start)
    )
    total_bids = total_bids_result.one() or 1

    total_clickouts_result = await session.exec(
        select(func.count(ClickoutEvent.id)).where(ClickoutEvent.created_at >= period_start)
    )
    total_clickouts = total_clickouts_result.one() or 0
    ctr = round(total_clickouts / max(total_bids, 1), 4)

    # M3: Clickout success rate (non-suspicious clickouts)
    suspicious_result = await session.exec(
        select(func.count(ClickoutEvent.id)).where(
            ClickoutEvent.created_at >= period_start,
            ClickoutEvent.is_suspicious == True,
        )
    )
    suspicious_count = suspicious_result.one() or 0
    clickout_success_rate = round((total_clickouts - suspicious_count) / max(total_clickouts, 1), 4)

    # M4: Affiliate handler coverage
    affiliate_tagged_result = await session.exec(
        select(func.count(ClickoutEvent.id)).where(
            ClickoutEvent.created_at >= period_start,
            ClickoutEvent.affiliate_tag.isnot(None),
        )
    )
    affiliate_tagged = affiliate_tagged_result.one() or 0
    affiliate_coverage = round(affiliate_tagged / max(total_clickouts, 1), 4)

    # Handler breakdown
    handler_breakdown_result = await session.exec(
        select(
            ClickoutEvent.handler_name,
            func.count(ClickoutEvent.id),
        ).where(
            ClickoutEvent.created_at >= period_start
        ).group_by(ClickoutEvent.handler_name)
    )
    handler_breakdown = {name: count for name, count in handler_breakdown_result.all()}

    # M5: Revenue per active user
    active_users_result = await session.exec(
        select(func.count(func.distinct(Row.user_id))).where(
            Row.created_at >= period_start
        )
    )
    active_users = active_users_result.one() or 1

    revenue_result = await session.exec(
        select(func.coalesce(func.sum(PurchaseEvent.platform_fee_amount), 0)).where(
            PurchaseEvent.created_at >= period_start
        )
    )
    period_revenue = float(revenue_result.one())
    revenue_per_user = round(period_revenue / max(active_users, 1), 2)

    # M8: K-factor (simplified)
    total_shares_result = await session.exec(
        select(func.count(ShareLink.id)).where(ShareLink.created_at >= period_start)
    )
    total_shares = total_shares_result.one() or 0

    referral_signups_result = await session.exec(
        select(func.count(User.id)).where(
            User.created_at >= period_start,
            User.referral_share_token.isnot(None),
        )
    )
    referral_signups = referral_signups_result.one() or 0

    # M9: GMV growth (current period vs previous)
    prev_start = period_start - timedelta(days=days)
    current_gmv_result = await session.exec(
        select(func.coalesce(func.sum(PurchaseEvent.amount), 0)).where(
            PurchaseEvent.created_at >= period_start
        )
    )
    current_gmv = float(current_gmv_result.one())

    prev_gmv_result = await session.exec(
        select(func.coalesce(func.sum(PurchaseEvent.amount), 0)).where(
            PurchaseEvent.created_at >= prev_start,
            PurchaseEvent.created_at < period_start,
        )
    )
    prev_gmv = float(prev_gmv_result.one())
    gmv_growth_rate = round((current_gmv - prev_gmv) / max(prev_gmv, 1), 4)

    # Funnel tracking (R6)
    visits = active_users  # Approximation: active users ≈ visits
    rows_created_result = await session.exec(
        select(func.count(Row.id)).where(Row.created_at >= period_start)
    )
    rows_created = rows_created_result.one() or 0

    purchases_result = await session.exec(
        select(func.count(PurchaseEvent.id)).where(PurchaseEvent.created_at >= period_start)
    )
    purchases = purchases_result.one() or 0

    return {
        "period": {"days": days, "from": period_start.isoformat(), "to": now.isoformat()},
        "m1_avg_time_to_first_result_seconds": round(float(avg_time_to_first_result_seconds), 1),
        "m2_offer_ctr": ctr,
        "m3_clickout_success_rate": clickout_success_rate,
        "m4_affiliate_coverage": affiliate_coverage,
        "m4_handler_breakdown": handler_breakdown,
        "m5_revenue_per_active_user": revenue_per_user,
        "m8_referral_signups": referral_signups,
        "m8_total_shares": total_shares,
        "m9_gmv_current_period": current_gmv,
        "m9_gmv_previous_period": prev_gmv,
        "m9_gmv_growth_rate": gmv_growth_rate,
        "funnel": {
            "active_users": active_users,
            "rows_created": rows_created,
            "bids_shown": total_bids,
            "clickouts": total_clickouts,
            "purchases": purchases,
            "suspicious_clickouts": suspicious_count,
        },
        "revenue": {
            "platform_total": period_revenue,
            "active_users": active_users,
        },
    }


@router.post("/admin/outreach/check-expired")
async def check_expired_outreach_endpoint(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Check for and process expired outreach events (PRD 12)."""
    from services.outreach_monitor import check_expired_outreach
    expired = await check_expired_outreach(session)
    return {"expired_count": len(expired), "expired": expired}


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
