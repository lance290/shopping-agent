"""
Outreach routes for vendor communication.
Handles sending RFP emails and tracking outreach events.
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from models import (
    Row, SellerQuote, OutreachEvent, VendorProfile,
    generate_magic_link_token,
)
from database import get_session
from dependencies import get_current_session
from utils.json_utils import safe_json_loads
from services.vendors import (
    search_checklist, get_checklist_summary, get_email_template,
)
from services.email import send_outreach_email, send_reminder_email

router = APIRouter(prefix="/outreach", tags=["outreach"])


class OutreachRequest(BaseModel):
    category: str
    vendor_limit: int = 5


class OutreachStatus(BaseModel):
    row_id: int
    status: str  # none, in_progress, complete
    total_sent: int
    opened: int
    clicked: int
    quoted: int
    vendors: List[dict]


class VendorInfo(BaseModel):
    name: str
    company: str
    email: str
    status: str  # sent, opened, clicked, quoted


@router.post("/rows/{row_id}/trigger")
async def trigger_outreach(
    row_id: int,
    request: OutreachRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Trigger vendor outreach for a row.
    Creates OutreachEvents and SellerQuotes (with magic links).
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get the row owned by the authenticated user
    result = await session.execute(
        select(Row).where(
            Row.id == row_id,
            Row.user_id == auth_session.user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Get vendors from VendorProfile directory
    normalized_category = request.category.lower().strip() if request.category else ""
    result = await session.execute(
        select(VendorProfile)
        .where(VendorProfile.category == normalized_category)
        .limit(request.vendor_limit)
    )
    vendor_profiles = result.scalars().all()
    if not vendor_profiles:
        raise HTTPException(
            status_code=404, 
            detail=f"No vendors found for category: {request.category}"
        )
    
    # Create outreach events and seller quotes for each vendor
    created_events = []
    for vp in vendor_profiles:
        if not vp.email:
            continue

        # Generate magic link token for this vendor
        token = generate_magic_link_token()
        
        # Create seller quote (pending, with magic link)
        quote = SellerQuote(
            row_id=row_id,
            token=token,
            token_expires_at=datetime.utcnow() + timedelta(days=7),
            seller_email=vp.email,
            seller_name=None,
            seller_company=vp.name,
            status="pending",
        )
        session.add(quote)
        
        # Create outreach event
        event = OutreachEvent(
            row_id=row_id,
            vendor_email=vp.email,
            vendor_name=None,
            vendor_company=vp.name,
            vendor_source="directory",
            quote_token=token,
            # sent_at will be set when email actually sends
        )
        session.add(event)
        created_events.append({
            "vendor": vp.name,
            "email": vp.email,
            "token": token,
        })
    
    # Update row status
    row.outreach_status = "in_progress"
    row.outreach_count = len(created_events)
    
    if not created_events:
        return {
            "status": "warning",
            "row_id": row_id,
            "vendors_contacted": 0,
            "detail": "All vendors for this category lack contact emails.",
            "events": [],
        }

    await session.commit()
    
    # Send emails (after commit so we have IDs)
    choice_factors = safe_json_loads(row.choice_factors, [])
    
    for event_info in created_events:
        email_result = await send_outreach_email(
            to_email=event_info["email"],
            to_name=event_info.get("name", ""),
            company_name=event_info["vendor"],
            request_summary=row.title,
            choice_factors=choice_factors,
            quote_token=event_info["token"],
        )
        
        # Update event with send status
        if email_result.success:
            result = await session.execute(
                select(OutreachEvent).where(OutreachEvent.quote_token == event_info["token"])
            )
            event = result.scalar_one_or_none()
            if event:
                event.sent_at = datetime.utcnow()
                event.message_id = email_result.message_id
    
    await session.commit()
    
    return {
        "status": "success",
        "row_id": row_id,
        "vendors_contacted": len(created_events),
        "events": created_events,
    }


@router.get("/rows/{row_id}/status", response_model=OutreachStatus)
async def get_outreach_status(
    row_id: int,
    session=Depends(get_session),
):
    """Get outreach status for a row."""
    # Get the row
    result = await session.execute(select(Row).where(Row.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Get all outreach events for this row
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.row_id == row_id)
    )
    events = result.scalars().all()
    
    # Calculate stats
    total_sent = sum(1 for e in events if e.sent_at)
    opened = sum(1 for e in events if e.opened_at)
    clicked = sum(1 for e in events if e.clicked_at)
    quoted = sum(1 for e in events if e.quote_submitted_at)
    
    # Build vendor list
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
    
    # Return 1x1 transparent gif
    from fastapi.responses import Response
    gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return Response(content=gif, media_type="image/gif")


@router.get("/vendors/search")
async def search_vendors_endpoint(
    q: str = "",
    category: Optional[str] = None,
    limit: int = 10,
    session=Depends(get_session),
):
    """
    Full-text search across vendor directory (VendorProfile table).
    Searches company, description, specialties, and profile_text via ILIKE.

    Examples:
      /outreach/vendors/search?q=starlink
      /outreach/vendors/search?q=gulfstream+argus
      /outreach/vendors/search?q=heavy&category=private_aviation
    """
    from sqlalchemy import or_

    stmt = select(VendorProfile)
    if category:
        stmt = stmt.where(VendorProfile.category == category.lower().strip())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                VendorProfile.name.ilike(pattern),
                VendorProfile.description.ilike(pattern),
                VendorProfile.specialties.ilike(pattern),
                VendorProfile.profile_text.ilike(pattern),
                VendorProfile.tagline.ilike(pattern),
            )
        )
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    profiles = result.scalars().all()

    vendors = []
    for vp in profiles:
        vendors.append({
            "title": vp.name,
            "description": vp.tagline or vp.description,
            "price": None,
            "url": vp.website or (f"mailto:{vp.email}" if vp.email else None),
            "image_url": vp.image_url,
            "source": "directory",
            "is_service_provider": True,
            "vendor_company": vp.name,
            "vendor_email": vp.email,
            "category": vp.category,
            "website": vp.website,
        })
    return {
        "query": q,
        "category": category,
        "total": len(vendors),
        "vendors": vendors,
    }


@router.get("/vendors/detail/{company_name}")
async def get_vendor_detail_endpoint(
    company_name: str,
    session=Depends(get_session),
):
    """Get full detail for a specific vendor by company name (partial match)."""
    result = await session.execute(
        select(VendorProfile).where(
            VendorProfile.name.ilike(f"%{company_name}%")
        )
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail=f"Vendor not found: {company_name}")
    return {
        "id": vp.id,
        "company": vp.name,
        "category": vp.category,
        "website": vp.website,
        "contact_email": vp.email,
        "contact_phone": vp.phone,
        "service_areas": vp.service_areas,
        "specialties": vp.specialties,
        "description": vp.description,
        "tagline": vp.tagline,
        "image_url": vp.image_url,
        "vendor_id": vp.id,
        "created_at": vp.created_at.isoformat() if vp.created_at else None,
    }


@router.get("/checklist")
async def get_checklist_endpoint(q: str = "", must_have_only: bool = False):
    """
    Get or search the charter due-diligence checklist.
    
    Examples:
      /outreach/checklist — full checklist
      /outreach/checklist?must_have_only=true — must-have items only
      /outreach/checklist?q=wifi — search for Wi-Fi items
      /outreach/checklist?q=cancellation — search for cancellation items
    """
    if q:
        items = search_checklist(q, must_have_only=must_have_only)
        return {"query": q, "must_have_only": must_have_only, "total": len(items), "items": items}
    
    summary = get_checklist_summary()
    if must_have_only:
        items = search_checklist("", must_have_only=True)
        return {"must_have_only": True, "total": len(items), "items": items, "summary": summary}
    
    items = search_checklist("")
    return {"total": len(items), "items": items, "summary": summary}


@router.get("/email-template")
async def get_email_template_endpoint():
    """Get the RFP email template for charter quote requests."""
    return get_email_template()


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
    """
    Send reminder emails to vendors who haven't responded after 48h.
    Skips opted-out vendors and those who already submitted quotes.
    """
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

    choice_factors = safe_json_loads(row.choice_factors, [])

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
