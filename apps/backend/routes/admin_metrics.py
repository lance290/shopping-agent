"""Admin metrics routes — core success metrics (PRD 09)."""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func, text

from database import get_session
from models import (
    User, Row, Bid, ClickoutEvent, PurchaseEvent, ShareLink,
)
from dependencies import require_admin

router = APIRouter(tags=["admin"])


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
