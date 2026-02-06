"""
Outreach routes for vendor communication.
Handles sending RFP emails and tracking outreach events.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from models import (
    Row, SellerQuote, OutreachEvent, User,
    generate_magic_link_token,
)
from database import get_session
from services.wattdata_mock import get_vendors, get_vendors_as_results, Vendor
from services.email import send_outreach_email

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


async def get_current_user(session=Depends(get_session)) -> User:
    """Placeholder - integrate with actual auth."""
    # For demo, return first user or create one
    result = await session.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="demo@buyanything.ai")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.post("/rows/{row_id}/trigger")
async def trigger_outreach(
    row_id: int,
    request: OutreachRequest,
    session=Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Trigger vendor outreach for a row.
    Creates OutreachEvents and SellerQuotes (with magic links).
    """
    # Get the row
    result = await session.execute(select(Row).where(Row.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Get vendors from mock WattData
    vendors: List[Vendor] = get_vendors(request.category, request.vendor_limit)
    if not vendors:
        raise HTTPException(
            status_code=404, 
            detail=f"No vendors found for category: {request.category}"
        )
    
    # Create outreach events and seller quotes for each vendor
    created_events = []
    for vendor in vendors:
        # Generate magic link token for this vendor
        token = generate_magic_link_token()
        
        # Create seller quote (pending, with magic link)
        quote = SellerQuote(
            row_id=row_id,
            token=token,
            token_expires_at=datetime.utcnow() + timedelta(days=7),
            seller_email=vendor.email,
            seller_name=vendor.name,
            seller_company=vendor.company,
            status="pending",
        )
        session.add(quote)
        
        # Create outreach event
        event = OutreachEvent(
            row_id=row_id,
            vendor_email=vendor.email,
            vendor_name=vendor.name,
            vendor_company=vendor.company,
            vendor_source=vendor.source,
            quote_token=token,
            # sent_at will be set when email actually sends
        )
        session.add(event)
        created_events.append({
            "vendor": vendor.company,
            "email": vendor.email,
            "token": token,
        })
    
    # Update row status
    row.outreach_status = "in_progress"
    row.outreach_count = len(vendors)
    
    await session.commit()
    
    # Send emails (after commit so we have IDs)
    import json
    choice_factors = []
    if row.choice_factors:
        try:
            choice_factors = json.loads(row.choice_factors)
        except (json.JSONDecodeError, TypeError):
            pass
    
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


@router.get("/vendors/{category}")
async def get_vendors_for_category(category: str, limit: int = 10):
    """Get vendors for a category as search result tiles."""
    vendors = get_vendors_as_results(category)
    return {
        "category": category,
        "vendors": vendors[:limit],
        "is_service": True,
    }


class PersistVendorsRequest(BaseModel):
    category: str
    vendors: List[dict]


@router.post("/rows/{row_id}/vendors")
async def persist_vendors_for_row(
    row_id: int,
    request: PersistVendorsRequest,
    session=Depends(get_session),
):
    """
    Persist vendor tiles as bids for a row.
    This ensures vendor tiles survive page reload.
    """
    from models import Bid, Seller
    from sqlmodel import delete
    
    # Verify row exists
    result = await session.execute(select(Row).where(Row.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Delete existing service provider bids for this row (to avoid duplicates)
    await session.execute(
        delete(Bid).where(
            Bid.row_id == row_id,
            Bid.is_service_provider == True
        )
    )
    
    # Create bids from vendors
    created_bids = []
    for vendor in request.vendors:
        vendor_company = vendor.get("vendor_company") or vendor.get("merchant") or vendor.get("title") or "Vendor"
        vendor_name = vendor.get("vendor_name") or vendor.get("contact_name")
        vendor_email = vendor.get("vendor_email") or vendor.get("contact_email")
        contact_phone = vendor.get("contact_phone")
        image_url = vendor.get("image_url")
        merchant_domain = vendor.get("merchant_domain")

        seller = None
        if vendor_company:
            seller_result = await session.execute(select(Seller).where(Seller.name == vendor_company))
            seller = seller_result.scalar_one_or_none()
            if not seller:
                seller = Seller(
                    name=vendor_company,
                    email=vendor_email,
                    domain=merchant_domain,
                    image_url=image_url,
                    category=request.category,
                    contact_name=vendor_name,
                    phone=contact_phone,
                )
                session.add(seller)
                await session.flush()
            else:
                updated = False
                if vendor_email and not seller.email:
                    seller.email = vendor_email
                    updated = True
                if merchant_domain and not seller.domain:
                    seller.domain = merchant_domain
                    updated = True
                if image_url and not seller.image_url:
                    seller.image_url = image_url
                    updated = True
                if vendor_name and not seller.contact_name:
                    seller.contact_name = vendor_name
                    updated = True
                if contact_phone and not seller.phone:
                    seller.phone = contact_phone
                    updated = True
                if request.category and not seller.category:
                    seller.category = request.category
                    updated = True
                if updated:
                    session.add(seller)

        price = vendor.get("price")
        normalized_price = float(price) if isinstance(price, (int, float)) else 0.0
        bid = Bid(
            row_id=row_id,
            seller_id=seller.id if seller else None,
            price=normalized_price,
            total_cost=normalized_price,
            currency=vendor.get("currency", "USD"),
            item_title=vendor.get("title") or vendor_company,
            item_url=vendor.get("url") or (f"mailto:{vendor_email}" if vendor_email else None),
            image_url=image_url,
            source=vendor.get("source", "wattdata"),
            is_service_provider=True,
            contact_name=vendor_name,
            contact_email=vendor_email,
            contact_phone=contact_phone,
        )
        session.add(bid)
        created_bids.append(bid)
    
    await session.commit()
    
    # Refresh to get IDs
    for bid in created_bids:
        await session.refresh(bid)
    
    return {
        "row_id": row_id,
        "persisted_count": len(created_bids),
        "bids": [{"id": b.id, "title": b.item_title} for b in created_bids],
    }


# REMOVED: /check-service endpoint was heuristic-based (keyword matching)
# All service detection is now handled by LLM via BFF's unified decision architecture
