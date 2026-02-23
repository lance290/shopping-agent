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
    Row, SellerQuote, OutreachEvent, VendorProfile, User,
    generate_magic_link_token,
)
from database import get_session
from dependencies import get_current_session
from utils.json_utils import safe_json_loads
from services.email import send_admin_vendor_alert
from services.vendors import (
    search_checklist, get_checklist_summary, get_email_template,
)
from services.email import send_outreach_email, send_reminder_email, send_custom_outreach_email
from services.llm import generate_outreach_email

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


class BlastRequest(BaseModel):
    subject: str  # e.g. "Looking for {{vendor_company}}'s help"
    body: str  # Plain text with {{vendor_name}}, {{vendor_company}}, {{row_title}} placeholders
    reply_to_email: str  # Replies go to this address
    sender_name: Optional[str] = "BuyAnything"
    dry_run: bool = False  # If true, return preview without sending


@router.post("/rows/{row_id}/blast")
async def blast_outreach(
    row_id: int,
    request: BlastRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Send a single email template to ALL vendors in a row.

    Template placeholders: {{vendor_name}}, {{vendor_company}}, {{row_title}}
    Each vendor gets a unique tracking pixel and quote link.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify row ownership
    result = await session.execute(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Find all vendor bids in this row that have vendor_id with email
    from models import Vendor, Bid
    bids_result = await session.execute(
        select(Bid).where(
            Bid.row_id == row_id,
            Bid.vendor_id.isnot(None),
            Bid.is_superseded == False,
        )
    )
    vendor_bids = bids_result.scalars().all()

    # Dedupe by vendor_id and collect vendor info
    seen_vendor_ids = set()
    targets = []
    for bid in vendor_bids:
        if bid.vendor_id in seen_vendor_ids:
            continue
        seen_vendor_ids.add(bid.vendor_id)
        v_result = await session.execute(select(Vendor).where(Vendor.id == bid.vendor_id))
        vendor = v_result.scalar_one_or_none()
        if vendor and vendor.email:
            targets.append({
                "vendor_id": vendor.id,
                "vendor_name": vendor.contact_name or vendor.name,
                "vendor_company": vendor.name,
                "vendor_email": vendor.email,
                "bid_id": bid.id,
            })

    # Also check OutreachEvents that already exist for this row — skip vendors already contacted
    existing_result = await session.execute(
        select(OutreachEvent.vendor_email).where(
            OutreachEvent.row_id == row_id,
            OutreachEvent.sent_at.isnot(None),
        )
    )
    already_contacted = {r[0].lower() for r in existing_result.all()}

    new_targets = [t for t in targets if t["vendor_email"].lower() not in already_contacted]

    if not new_targets:
        return {
            "status": "no_new_vendors",
            "row_id": row_id,
            "total_vendors": len(targets),
            "already_contacted": len(already_contacted),
            "sent": 0,
        }

    # Dry run — return preview of what would be sent
    if request.dry_run:
        previews = []
        for t in new_targets:
            subj = request.subject.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
            bod = request.body.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
            previews.append({"to": t["vendor_email"], "subject": subj, "body_preview": bod[:200]})
        return {
            "status": "dry_run",
            "row_id": row_id,
            "would_send": len(new_targets),
            "already_contacted": len(already_contacted),
            "previews": previews,
        }

    # Create SellerQuote + OutreachEvent per vendor, personalize, and send
    from services.email import send_custom_outreach_email, get_quote_url, get_tracking_pixel_url
    import os
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    sent = []
    failed = []
    for t in new_targets:
        token = generate_magic_link_token()

        # Create SellerQuote with magic link
        quote = SellerQuote(
            row_id=row_id,
            token=token,
            token_expires_at=datetime.utcnow() + timedelta(days=14),
            seller_email=t["vendor_email"],
            seller_name=t["vendor_name"],
            seller_company=t["vendor_company"],
            status="pending",
        )
        session.add(quote)

        # Create OutreachEvent
        event = OutreachEvent(
            row_id=row_id,
            vendor_email=t["vendor_email"],
            vendor_name=t["vendor_name"],
            vendor_company=t["vendor_company"],
            vendor_source="blast",
            quote_token=token,
        )
        session.add(event)

        # Personalize template
        subj = request.subject.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
        body_text = request.body.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")

        # Build HTML with tracking pixel and quote link
        quote_url = get_quote_url(token)
        tracking_url = get_tracking_pixel_url(token)
        unsubscribe_url = f"{backend_url}/outreach/unsubscribe/{token}"

        body_html = body_text.replace("\n", "<br>")
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto;">
            {body_html}

            <p style="text-align: center; margin: 30px 0;">
                <a href="{quote_url}"
                   style="background: #2563eb; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Submit Your Quote
                </a>
            </p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #999; font-size: 12px;">
                Sent on behalf of {request.sender_name} via BuyAnything
                <br><a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a>
            </p>
            <p style="color: #bbb; font-size: 10px;">
                BuyAnything.ai is a marketplace platform. We may earn a referral fee or commission
                when transactions are completed through our platform.
            </p>
            <img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">
        </div>
        """

        email_result = await send_custom_outreach_email(
            to_email=t["vendor_email"],
            to_name=t["vendor_name"],
            company_name=t["vendor_company"],
            subject=subj,
            body_text=body_text,
            quote_token=token,
            reply_to_email=request.reply_to_email,
            sender_name=request.sender_name or "BuyAnything",
        )

        if email_result.success:
            event.sent_at = datetime.utcnow()
            event.message_id = email_result.message_id
            sent.append({"vendor": t["vendor_company"], "email": t["vendor_email"]})
        else:
            failed.append({"vendor": t["vendor_company"], "email": t["vendor_email"], "error": email_result.error})

    # Update row
    row.outreach_status = "in_progress"
    row.outreach_count = (row.outreach_count or 0) + len(sent)

    await session.commit()

    # Admin alert
    await send_admin_vendor_alert(
        event_type="blast_sent",
        vendor_name=f"{len(sent)} vendors",
        row_title=row.title,
        row_id=row_id,
    )

    return {
        "status": "success",
        "row_id": row_id,
        "sent": len(sent),
        "failed": len(failed),
        "already_contacted": len(already_contacted),
        "details": sent,
        "errors": failed if failed else None,
    }


class SendOutreachRequest(BaseModel):
    vendor_email: str
    vendor_name: Optional[str] = None
    vendor_company: str
    subject: Optional[str] = None
    body: Optional[str] = None
    reply_to_email: str
    sender_name: Optional[str] = None
    sender_role: Optional[str] = None
    sender_company: Optional[str] = None


class QuoteLinkRequest(BaseModel):
    vendor_email: str
    vendor_name: Optional[str] = None
    vendor_company: str


@router.post("/rows/{row_id}/send")
async def send_outreach(
    row_id: int,
    request: SendOutreachRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Generate + send a vendor outreach email via Resend.

    If subject/body are provided, use them directly (user edited).
    If not, LLM generates from chat context.
    Reply-to is set to the user's email — vendor replies go to them.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify row ownership
    result = await session.execute(
        select(Row).where(
            Row.id == row_id,
            Row.user_id == auth_session.user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Generate email via LLM if not provided
    subject = request.subject
    body = request.body
    if not subject or not body:
        generated = await generate_outreach_email(
            row_title=row.title or "",
            vendor_company=request.vendor_company,
            sender_name=request.sender_name,
            sender_role=request.sender_role,
            chat_history=row.chat_history,
            choice_answers=row.choice_answers,
            search_intent=row.search_intent,
            sender_company=request.sender_company,
        )
        subject = subject or generated["subject"]
        body = body or generated["body"]

    # Create outreach record + quote link
    token = generate_magic_link_token()

    quote = SellerQuote(
        row_id=row_id,
        token=token,
        token_expires_at=datetime.utcnow() + timedelta(days=14),
        seller_email=request.vendor_email,
        seller_name=request.vendor_name,
        seller_company=request.vendor_company,
        status="pending",
    )
    session.add(quote)

    event = OutreachEvent(
        row_id=row_id,
        vendor_email=request.vendor_email,
        vendor_name=request.vendor_name,
        vendor_company=request.vendor_company,
        vendor_source="modal",
        quote_token=token,
    )
    session.add(event)
    await session.commit()

    # Send via Resend with reply-to
    email_result = await send_custom_outreach_email(
        to_email=request.vendor_email,
        vendor_company=request.vendor_company,
        subject=subject,
        body_text=body,
        quote_token=token,
        reply_to_email=request.reply_to_email,
        sender_name=request.sender_name,
    )

    # Update event with send status
    if email_result.success and email_result.message_id:
        result = await session.execute(
            select(OutreachEvent).where(OutreachEvent.quote_token == token)
        )
        evt = result.scalar_one_or_none()
        if evt:
            evt.sent_at = datetime.utcnow()
            evt.message_id = email_result.message_id

        # Persist user profile fields from outreach modal
        if auth_session.user_id:
            user = await session.get(User, auth_session.user_id)
            if user:
                if request.reply_to_email and not user.email:
                    user.email = request.reply_to_email
                if request.sender_name and not user.name:
                    user.name = request.sender_name
                if request.sender_company and not user.company:
                    user.company = request.sender_company

        await session.commit()

    return {
        "status": "sent" if email_result.success else "error",
        "message_id": email_result.message_id,
        "error": email_result.error,
        "subject": subject,
        "body": body,
        "quote_token": token,
    }


@router.post("/rows/{row_id}/generate-email")
async def generate_email_preview(
    row_id: int,
    request: SendOutreachRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Generate an email preview using the LLM without sending.
    Called when the modal opens to pre-populate the email.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.execute(
        select(Row).where(
            Row.id == row_id,
            Row.user_id == auth_session.user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    generated = await generate_outreach_email(
        row_title=row.title or "",
        vendor_company=request.vendor_company,
        sender_name=request.sender_name,
        sender_role=request.sender_role,
        chat_history=row.chat_history,
        choice_answers=row.choice_answers,
        search_intent=row.search_intent,
        sender_company=request.sender_company,
    )

    return generated


@router.post("/rows/{row_id}/quote-link")
async def create_quote_link(
    row_id: int,
    request: QuoteLinkRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Create a single-vendor quote link for the VendorContactModal.

    The EA reviews the email, clicks Send (mailto:), and the email body
    includes a tracked /quote/[token] link. The vendor clicks the link,
    submits a formal quote on our platform, and enters the viral loop.

    Returns the token so the frontend can build the full URL.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify row ownership
    result = await session.execute(
        select(Row).where(
            Row.id == row_id,
            Row.user_id == auth_session.user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Check for existing quote link for this vendor+row (avoid duplicates)
    existing = await session.execute(
        select(SellerQuote).where(
            SellerQuote.row_id == row_id,
            SellerQuote.seller_email == request.vendor_email,
            SellerQuote.status == "pending",
        )
    )
    existing_quote = existing.scalar_one_or_none()
    if existing_quote and existing_quote.token_expires_at and existing_quote.token_expires_at > datetime.utcnow():
        # Reuse existing valid token
        return {
            "token": existing_quote.token,
            "quote_url": f"/quote/{existing_quote.token}",
            "expires_at": existing_quote.token_expires_at.isoformat(),
            "reused": True,
        }

    # Generate fresh token
    token = generate_magic_link_token()

    quote = SellerQuote(
        row_id=row_id,
        token=token,
        token_expires_at=datetime.utcnow() + timedelta(days=14),
        seller_email=request.vendor_email,
        seller_name=request.vendor_name,
        seller_company=request.vendor_company,
        status="pending",
    )
    session.add(quote)

    event = OutreachEvent(
        row_id=row_id,
        vendor_email=request.vendor_email,
        vendor_name=request.vendor_name,
        vendor_company=request.vendor_company,
        vendor_source="modal",
        quote_token=token,
    )
    session.add(event)

    await session.commit()

    return {
        "token": token,
        "quote_url": f"/quote/{token}",
        "expires_at": (datetime.utcnow() + timedelta(days=14)).isoformat(),
        "reused": False,
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

        # Look up the row title for context
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


@router.get("/rows/{row_id}/contact-statuses")
async def get_contact_statuses(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Return outreach status per vendor_email for a row.
    Used by frontend to show "Contacted" / "Quote Received" badges on offer tiles.

    Returns: { statuses: { [vendor_email]: { status, sent_at, quoted_at } } }
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify row ownership
    result = await session.execute(
        select(Row).where(
            Row.id == row_id,
            Row.user_id == auth_session.user_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Get all outreach events for this row
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.row_id == row_id)
    )
    events = result.scalars().all()

    # Get all submitted seller quotes for this row
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
