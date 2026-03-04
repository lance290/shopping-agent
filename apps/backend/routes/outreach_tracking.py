"""
Outreach tracking, status, reminders, unsubscribe, and contact-status routes.

Extracted from routes/outreach.py to keep files under 450 lines.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from models import Row, SellerQuote, OutreachEvent
from database import get_session
from dependencies import get_current_session
from utils.json_utils import safe_json_loads
from services.email import send_admin_vendor_alert, send_reminder_email

router = APIRouter(prefix="/outreach", tags=["outreach"])


class OutreachStatus(BaseModel):
    row_id: int
    status: str
    total_sent: int
    opened: int
    clicked: int
    quoted: int
    vendors: List[dict]


@router.get("/rows/{row_id}/status", response_model=OutreachStatus)
async def get_outreach_status(
    row_id: int,
    session=Depends(get_session),
):
    """Get outreach status for a row."""
    result = await session.execute(select(Row).where(Row.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.row_id == row_id)
    )
    events = result.scalars().all()

    total_sent = sum(1 for e in events if e.sent_at)
    opened = sum(1 for e in events if e.opened_at)
    clicked = sum(1 for e in events if e.clicked_at)
    quoted = sum(1 for e in events if e.quote_submitted_at)

    vendors = []
    for event in events:
        status = "pending"
        if event.quote_submitted_at:
            status = "quoted"
        elif event.clicked_at:
            status = "clicked"
        elif event.opened_at:
            status = "opened"
        elif event.sent_at:
            status = "sent"

        vendors.append({
            "name": event.vendor_name,
            "company": event.vendor_company,
            "email": event.vendor_email,
            "status": status,
        })

    return OutreachStatus(
        row_id=row_id,
        status=row.outreach_status or "none",
        total_sent=total_sent,
        opened=opened,
        clicked=clicked,
        quoted=quoted,
        vendors=vendors,
    )


@router.post("/events/{event_id}/mark-sent")
async def mark_event_sent(
    event_id: int,
    message_id: Optional[str] = None,
    session=Depends(get_session),
):
    """Mark an outreach event as sent (called after email sends)."""
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.sent_at = datetime.utcnow()
    if message_id:
        event.message_id = message_id

    await session.commit()
    return {"status": "marked_sent", "event_id": event_id}


@router.get("/track/open/{token}")
async def track_email_open(token: str, session=Depends(get_session)):
    """Track email open via pixel (1x1 gif)."""
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.quote_token == token)
    )
    event = result.scalar_one_or_none()
    if event and not event.opened_at:
        event.opened_at = datetime.utcnow()
        await session.commit()

        row_title = None
        row_result = await session.execute(select(Row).where(Row.id == event.row_id))
        row = row_result.scalar_one_or_none()
        if row:
            row_title = row.title

        await send_admin_vendor_alert(
            event_type="opened",
            vendor_name=event.vendor_name,
            vendor_email=event.vendor_email,
            vendor_company=event.vendor_company,
            row_title=row_title,
            row_id=event.row_id,
        )

    from fastapi.responses import Response
    gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return Response(content=gif, media_type="image/gif")


@router.get("/unsubscribe/{token}")
async def unsubscribe_vendor(token: str, session=Depends(get_session)):
    """Vendor opts out of future outreach via email link."""
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.quote_token == token)
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"status": "not_found", "message": "Link not recognized."}

    event.opt_out = True
    await session.commit()
    return {"status": "unsubscribed", "message": "You have been unsubscribed from future requests."}


@router.post("/rows/{row_id}/reminders")
async def send_reminders(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """Send reminder emails to vendors who haven't responded after 48h."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await session.execute(select(Row).where(Row.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    cutoff = datetime.utcnow() - timedelta(hours=48)
    result = await session.execute(
        select(OutreachEvent).where(
            OutreachEvent.row_id == row_id,
            OutreachEvent.sent_at != None,
            OutreachEvent.sent_at < cutoff,
            OutreachEvent.quote_submitted_at == None,
            OutreachEvent.opt_out == False,
        )
    )
    events = result.scalars().all()

    if not events:
        return {"status": "no_reminders", "sent": 0}

    sent_count = 0
    for event in events:
        if not event.quote_token:
            continue
        email_result = await send_reminder_email(
            to_email=event.vendor_email,
            to_name=event.vendor_name or "",
            company_name=event.vendor_company or "Vendor",
            request_summary=row.title,
            quote_token=event.quote_token,
        )
        if email_result.success:
            sent_count += 1

    return {"status": "reminders_sent", "sent": sent_count, "total_eligible": len(events)}


@router.get("/rows/{row_id}/contact-statuses")
async def get_contact_statuses(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """Return outreach status per vendor_email for a row."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.execute(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.row_id == row_id)
    )
    events = result.scalars().all()

    result = await session.execute(
        select(SellerQuote).where(
            SellerQuote.row_id == row_id,
            SellerQuote.status == "submitted",
        )
    )
    submitted_quotes = result.scalars().all()
    quoted_emails = {q.seller_email.lower() for q in submitted_quotes if q.seller_email}

    statuses: dict = {}
    for evt in events:
        email_key = evt.vendor_email.lower()
        has_quote = email_key in quoted_emails
        if has_quote:
            status = "quoted"
        elif evt.sent_at:
            status = "contacted"
        else:
            status = "pending"

        statuses[email_key] = {
            "status": status,
            "sent_at": evt.sent_at.isoformat() if evt.sent_at else None,
            "quoted_at": evt.quote_submitted_at.isoformat() if evt.quote_submitted_at else None,
            "vendor_company": evt.vendor_company,
        }

    return {"statuses": statuses}
