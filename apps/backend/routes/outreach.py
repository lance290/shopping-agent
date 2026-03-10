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
    Send a vendor outreach email via proxy relay (Deal pipeline).

    Creates a Deal with a proxy email alias so vendor replies come back
    through our relay and get shown in the app. No quote form link —
    the vendor simply replies to the email with their offer.
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
            structured_constraints=row.structured_constraints,
            sender_company=request.sender_company,
        )
        subject = subject or generated["subject"]
        body = body or generated["body"]

    # Resolve vendor_id from Vendor table by email (if exists)
    from models import Vendor
    vendor_id = None
    if request.vendor_email:
        v_result = await session.execute(
            select(Vendor).where(Vendor.email == request.vendor_email).limit(1)
        )
        vendor = v_result.scalar_one_or_none()
        if vendor:
            vendor_id = vendor.id

    # Create a Deal with proxy email alias for relay
    from services.deal_pipeline import create_deal, record_message, MESSAGES_DOMAIN
    deal = await create_deal(
        session=session,
        row_id=row_id,
        buyer_user_id=auth_session.user_id,
        vendor_id=vendor_id,
    )
    proxy_address = f"{deal.proxy_email_alias}@{MESSAGES_DOMAIN}"

    # Create outreach event for tracking
    event = OutreachEvent(
        row_id=row_id,
        vendor_email=request.vendor_email,
        vendor_name=request.vendor_name,
        vendor_company=request.vendor_company,
        vendor_source="modal",
    )
    session.add(event)
    await session.commit()

    # Send via Resend through the proxy alias (vendor replies come back to relay)
    from services.email import send_deal_outreach_email
    email_result = await send_deal_outreach_email(
        to_email=request.vendor_email,
        vendor_company=request.vendor_company,
        subject=subject,
        body_text=body,
        proxy_address=proxy_address,
        sender_name=request.sender_name,
    )

    # Record the outreach as the first message in the deal ledger
    if email_result.success:
        await record_message(
            session=session,
            deal_id=deal.id,
            sender_type="buyer",
            content_text=body,
            sender_email=proxy_address,
            subject=subject,
            resend_message_id=email_result.message_id,
        )
        event.sent_at = datetime.utcnow()
        event.message_id = email_result.message_id

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
        "deal_id": deal.id,
        "proxy_email": proxy_address,
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
        structured_constraints=row.structured_constraints,
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

