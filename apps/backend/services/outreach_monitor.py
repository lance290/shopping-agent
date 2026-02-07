"""Outreach timeout monitoring service (PRD 12).

Checks for expired outreach events and notifies buyers.
Suggests alternatives when vendors don't respond.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import OutreachEvent, Row, Bid, Notification

logger = logging.getLogger(__name__)


async def check_expired_outreach(session: AsyncSession) -> List[dict]:
    """
    Find outreach events that have exceeded their timeout window.
    Mark them as expired and notify the buyer.

    Returns list of expired outreach summaries.
    """
    now = datetime.utcnow()

    # Find outreach events that are sent but not responded and past timeout
    result = await session.exec(
        select(OutreachEvent).where(
            OutreachEvent.status.in_(["sent", "delivered", "opened"]),
            OutreachEvent.expired_at.is_(None),
            OutreachEvent.sent_at.isnot(None),
        )
    )
    events = result.all()

    expired_summaries = []

    for event in events:
        if not event.sent_at:
            continue

        deadline = event.sent_at + timedelta(hours=event.timeout_hours)
        if now < deadline:
            continue

        # Mark as expired
        event.status = "expired"
        event.expired_at = now
        session.add(event)

        # Notify buyer
        row = await session.get(Row, event.row_id)
        if row and row.user_id:
            vendor_name = event.vendor_name or event.vendor_company or event.vendor_email
            notif = Notification(
                user_id=row.user_id,
                type="outreach_expired",
                title=f"Vendor didn't respond: {vendor_name}",
                body=f"No response received for \"{row.title}\" after {event.timeout_hours}h. We suggest checking your other options.",
                action_url=f"/projects?row={row.id}",
                resource_type="row",
                resource_id=row.id,
            )
            session.add(notif)

        expired_summaries.append({
            "outreach_id": event.id,
            "row_id": event.row_id,
            "vendor_email": event.vendor_email,
            "timeout_hours": event.timeout_hours,
        })

    if expired_summaries:
        await session.commit()
        logger.info(f"[OutreachMonitor] Expired {len(expired_summaries)} outreach events")

    return expired_summaries


async def send_followup(session: AsyncSession, outreach_id: int) -> Optional[dict]:
    """
    Send a follow-up reminder for an outreach that hasn't received a response.
    Only sends if no follow-up has been sent yet and the event hasn't expired.
    """
    event = await session.get(OutreachEvent, outreach_id)
    if not event:
        return None

    if event.status == "expired":
        return {"error": "Outreach already expired"}

    if event.followup_sent_at:
        return {"error": "Follow-up already sent"}

    if event.status == "responded":
        return {"error": "Vendor already responded"}

    # Mark follow-up as sent
    event.followup_sent_at = datetime.utcnow()
    session.add(event)

    # Send follow-up email via existing email service
    try:
        from services.email import send_reminder_email
        row = await session.get(Row, event.row_id)
        request_summary = row.title if row else "your request"
        await send_reminder_email(
            to_email=event.vendor_email,
            to_name=event.vendor_name or "Vendor",
            company_name=event.vendor_company or "",
            request_summary=request_summary,
            quote_token=event.quote_token or "",
        )
    except Exception as e:
        logger.error(f"[OutreachMonitor] Follow-up email failed: {e}")

    await session.commit()

    return {
        "outreach_id": event.id,
        "followup_sent_at": event.followup_sent_at.isoformat(),
        "vendor_email": event.vendor_email,
    }


async def suggest_alternatives(session: AsyncSession, row_id: int) -> List[dict]:
    """
    When a vendor doesn't respond, suggest existing bids from other sources.
    Returns top 3 alternative bids sorted by score.
    """
    result = await session.exec(
        select(Bid)
        .where(Bid.row_id == row_id, Bid.is_selected == False)
        .order_by(Bid.combined_score.desc().nullslast())
        .limit(3)
    )
    bids = result.all()

    return [
        {
            "bid_id": b.id,
            "title": b.item_title,
            "price": b.price,
            "source": b.source,
            "score": b.combined_score,
        }
        for b in bids
    ]
