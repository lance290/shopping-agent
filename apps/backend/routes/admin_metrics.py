"""Admin metrics routes — core success metrics (PRD 09)."""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func, text

from database import get_session
from models import (
    User, Row, Bid, ClickoutEvent, PurchaseEvent, ShareLink,
    RequestFeedback, RequestEvent,
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


@router.get("/admin/trust-metrics")
async def admin_trust_metrics(
    days: int = 30,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Trust-oriented metrics derived from RequestFeedback and RequestEvent tables.

    Covers PRD sections 7, 10, 12:
    - request resolution rate (outcome breakdown)
    - candidate feedback distribution
    - search event funnel
    - feedback volume by type
    - top failure modes
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # ── Outcome breakdown (request resolution rate) ────────────────────────
    outcome_result = await session.exec(
        select(Row.row_outcome, func.count(Row.id))
        .where(
            Row.updated_at >= period_start,
            Row.row_outcome.isnot(None),
        )
        .group_by(Row.row_outcome)
    )
    outcome_counts: dict[str, int] = {o: c for o, c in outcome_result.all()}
    total_with_outcome = sum(outcome_counts.values())
    rows_with_outcome_result = await session.exec(
        select(func.count(Row.id)).where(
            Row.created_at >= period_start,
        )
    )
    total_rows_period = rows_with_outcome_result.one() or 0
    resolution_rate = round(
        outcome_counts.get("solved", 0) / max(total_with_outcome, 1), 4
    )
    partial_rate = round(
        outcome_counts.get("partially_solved", 0) / max(total_with_outcome, 1), 4
    )
    not_solved_rate = round(
        outcome_counts.get("not_solved", 0) / max(total_with_outcome, 1), 4
    )
    outcome_coverage = round(total_with_outcome / max(total_rows_period, 1), 4)

    # ── Feedback distribution ──────────────────────────────────────────────
    feedback_result = await session.exec(
        select(RequestFeedback.feedback_type, func.count(RequestFeedback.id))
        .where(RequestFeedback.created_at >= period_start)
        .group_by(RequestFeedback.feedback_type)
    )
    feedback_by_type: dict[str, int] = {ft: c for ft, c in feedback_result.all()}
    total_feedback = sum(feedback_by_type.values())
    good_lead_rate = round(
        feedback_by_type.get("good_lead", 0) / max(total_feedback, 1), 4
    )
    negative_types = {"irrelevant", "wrong_geography", "not_premium_enough",
                      "too_expensive", "missing_contact_info", "unsafe_or_low_trust"}
    negative_feedback = sum(feedback_by_type.get(t, 0) for t in negative_types)
    negative_rate = round(negative_feedback / max(total_feedback, 1), 4)

    # ── Search event funnel ────────────────────────────────────────────────
    event_result = await session.exec(
        select(RequestEvent.event_type, func.count(RequestEvent.id))
        .where(RequestEvent.created_at >= period_start)
        .group_by(RequestEvent.event_type)
    )
    event_counts: dict[str, int] = {et: c for et, c in event_result.all()}

    searches_requested = event_counts.get("search_requested", 0) + event_counts.get("search_stream_requested", 0)
    searches_completed = event_counts.get("search_completed", 0)
    candidates_clicked = event_counts.get("candidate_clicked", 0)
    candidates_saved = event_counts.get("candidate_saved", 0)
    candidates_selected = event_counts.get("candidate_selected", 0)
    outcomes_recorded = event_counts.get("outcome_recorded", 0)
    feedback_submitted = event_counts.get("feedback_submitted", 0)

    search_completion_rate = round(
        searches_completed / max(searches_requested, 1), 4
    )
    click_through_rate = round(
        candidates_clicked / max(searches_completed, 1), 4
    )
    save_rate = round(
        candidates_saved / max(searches_completed, 1), 4
    )
    acted_on_rate = round(
        candidates_selected / max(searches_completed, 1), 4
    )
    trusted_result_rate = round(
        feedback_by_type.get("good_lead", 0) / max(searches_completed, 1), 4
    )

    # ── Average feedback score ─────────────────────────────────────────────
    avg_score_result = await session.exec(
        select(func.avg(RequestFeedback.score)).where(
            RequestFeedback.created_at >= period_start,
            RequestFeedback.score.isnot(None),
        )
    )
    avg_feedback_score = avg_score_result.one()
    avg_feedback_score = round(float(avg_feedback_score), 3) if avg_feedback_score else None

    # ── Time-to-trusted-option (seconds from row creation to first candidate_clicked) ──
    ttto_result = await session.execute(
        text(
            "SELECT AVG(EXTRACT(EPOCH FROM (first_click.created_at - r.created_at))) "
            "FROM row r "
            "JOIN LATERAL ( "
            "  SELECT created_at FROM request_event "
            "  WHERE request_event.row_id = r.id "
            "  AND request_event.event_type = 'candidate_clicked' "
            "  ORDER BY created_at LIMIT 1 "
            ") first_click ON true "
            "WHERE r.created_at >= :period_start"
        ),
        {"period_start": period_start},
    )
    avg_ttto = ttto_result.scalar()
    avg_time_to_trusted_option_seconds = round(float(avg_ttto), 1) if avg_ttto else None

    # ── Routing mode breakdown ──────────────────────────────────────────────
    routing_mode_result = await session.exec(
        select(Row.routing_mode, func.count(Row.id))
        .where(
            Row.created_at >= period_start,
            Row.routing_mode.isnot(None),
        )
        .group_by(Row.routing_mode)
    )
    routing_mode_counts: dict[str, int] = {m: c for m, c in routing_mode_result.all()}

    # ── Outcome by routing mode (PRD §12: quality by route type) ──────────
    outcome_by_route_result = await session.exec(
        select(Row.routing_mode, Row.row_outcome, func.count(Row.id))
        .where(
            Row.updated_at >= period_start,
            Row.row_outcome.isnot(None),
            Row.routing_mode.isnot(None),
        )
        .group_by(Row.routing_mode, Row.row_outcome)
    )
    outcome_by_route: dict[str, dict[str, int]] = {}
    for mode, outcome, cnt in outcome_by_route_result.all():
        outcome_by_route.setdefault(mode, {})[outcome] = cnt

    # ── Provider click breakdown (PRD §12: quality by provider) ───────────
    provider_click_result = await session.exec(
        select(RequestEvent.event_value, func.count(RequestEvent.id))
        .where(
            RequestEvent.created_at >= period_start,
            RequestEvent.event_type == "candidate_clicked",
            RequestEvent.event_value.isnot(None),
        )
        .group_by(RequestEvent.event_value)
    )
    clicks_by_provider: dict[str, int] = {prov: cnt for prov, cnt in provider_click_result.all()}

    # ── Per-user cohort summary (PRD §7.4: cohort-level metrics) ──────────
    cohort_result = await session.execute(
        text(
            "SELECT u.id, u.email, "
            "  COUNT(DISTINCT r.id) AS total_rows, "
            "  COUNT(DISTINCT CASE WHEN r.row_outcome = 'solved' THEN r.id END) AS solved, "
            "  COUNT(DISTINCT CASE WHEN r.row_outcome IS NOT NULL THEN r.id END) AS with_outcome, "
            "  COUNT(DISTINCT re.id) FILTER (WHERE re.event_type = 'candidate_clicked') AS clicks, "
            "  COUNT(DISTINCT rf.id) AS feedbacks "
            "FROM \"user\" u "
            "JOIN row r ON r.user_id = u.id AND r.created_at >= :period_start "
            "LEFT JOIN request_event re ON re.row_id = r.id AND re.created_at >= :period_start "
            "LEFT JOIN request_feedback rf ON rf.row_id = r.id AND rf.created_at >= :period_start "
            "GROUP BY u.id, u.email "
            "ORDER BY total_rows DESC "
            "LIMIT 50"
        ),
        {"period_start": period_start},
    )
    cohort_rows = cohort_result.fetchall()
    cohort_summary = [
        {
            "user_id": row[0],
            "email": row[1],
            "total_rows": row[2],
            "solved": row[3],
            "with_outcome": row[4],
            "resolution_rate": round(row[3] / max(row[4], 1), 4),
            "clicks": row[5],
            "feedbacks": row[6],
        }
        for row in cohort_rows
    ]

    # ── Outcome by desire_tier (PRD §2.4: commodity vs high-touch) ────────
    outcome_by_tier_result = await session.exec(
        select(Row.desire_tier, Row.row_outcome, func.count(Row.id))
        .where(
            Row.updated_at >= period_start,
            Row.row_outcome.isnot(None),
            Row.desire_tier.isnot(None),
        )
        .group_by(Row.desire_tier, Row.row_outcome)
    )
    outcome_by_tier: dict[str, dict[str, int]] = {}
    for tier, outcome, cnt in outcome_by_tier_result.all():
        outcome_by_tier.setdefault(tier, {})[outcome] = cnt

    return {
        "period": {"days": days, "from": period_start.isoformat(), "to": now.isoformat()},
        "resolution": {
            "outcome_coverage_rate": outcome_coverage,
            "resolution_rate": resolution_rate,
            "partial_rate": partial_rate,
            "not_solved_rate": not_solved_rate,
            "outcome_breakdown": outcome_counts,
            "total_rows_period": total_rows_period,
            "total_with_outcome": total_with_outcome,
        },
        "feedback": {
            "total": total_feedback,
            "good_lead_rate": good_lead_rate,
            "negative_rate": negative_rate,
            "by_type": feedback_by_type,
            "avg_score": avg_feedback_score,
        },
        "search_funnel": {
            "searches_requested": searches_requested,
            "searches_completed": searches_completed,
            "search_completion_rate": search_completion_rate,
            "candidates_clicked": candidates_clicked,
            "candidates_saved": candidates_saved,
            "candidates_selected": candidates_selected,
            "click_through_rate": click_through_rate,
            "save_rate": save_rate,
            "acted_on_rate": acted_on_rate,
            "trusted_result_rate": trusted_result_rate,
            "outcomes_recorded": outcomes_recorded,
            "feedback_submitted": feedback_submitted,
            "avg_time_to_trusted_option_seconds": avg_time_to_trusted_option_seconds,
        },
        "routing": {
            "mode_breakdown": routing_mode_counts,
            "outcome_by_route": outcome_by_route,
        },
        "provider": {
            "clicks_by_provider": clicks_by_provider,
        },
        "cohort": cohort_summary,
        "desire_tier": {
            "outcome_by_tier": outcome_by_tier,
        },
        "all_event_counts": event_counts,
    }
