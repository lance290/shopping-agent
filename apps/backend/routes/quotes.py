"""
Quote routes for seller quote submission.
Handles magic link validation and quote-to-bid conversion.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from models import (
    Row, SellerQuote, OutreachEvent, Bid, DealHandoff, User,
)
from database import get_session
from dependencies import get_current_session
from services.email import send_handoff_buyer_email, send_handoff_seller_email, send_admin_vendor_alert
from utils.json_utils import safe_json_loads

router = APIRouter(prefix="/quotes", tags=["quotes"])


class QuoteFormData(BaseModel):
    """Data shown on quote form (read-only context)."""
    row_id: int
    row_title: str
    buyer_request: str
    choice_factors: List[dict]
    seller_email: str
    seller_company: Optional[str]
    expires_at: Optional[str]


class QuoteSubmission(BaseModel):
    """Seller's quote submission."""
    price: float
    currency: str = "USD"
    description: str
    aircraft_type: Optional[str] = None  # For private jet demo
    includes_catering: Optional[bool] = None
    availability_confirmed: bool = True
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    answers: Optional[dict] = None  # Generic choice factor answers


class QuoteResponse(BaseModel):
    quote_id: int
    status: str
    message: str


@router.get("/form/{token}", response_model=QuoteFormData)
async def get_quote_form(token: str, session=Depends(get_session)):
    """
    Get quote form data by magic link token.
    Returns context for the quote submission form.
    """
    # Find the seller quote by token
    result = await session.execute(
        select(SellerQuote).where(SellerQuote.token == token)
    )
    quote = result.scalar_one_or_none()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    # Check expiration
    if quote.token_expires_at and quote.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This link has expired")
    
    # Check if already submitted
    if quote.status == "submitted":
        raise HTTPException(status_code=400, detail="Quote already submitted")
    
    # Get the row for context
    result = await session.execute(select(Row).where(Row.id == quote.row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Record click on the outreach event
    oe_result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.quote_token == token)
    )
    oe = oe_result.scalar_one_or_none()
    if oe and not oe.clicked_at:
        oe.clicked_at = datetime.utcnow()
        await session.commit()

        await send_admin_vendor_alert(
            event_type="clicked",
            vendor_name=quote.seller_name,
            vendor_email=quote.seller_email,
            vendor_company=quote.seller_company,
            row_title=row.title,
            row_id=row.id,
        )

    # Parse choice factors if available
    choice_factors = safe_json_loads(row.choice_factors, [])
    
    # For demo, add private jet specific factors if not present
    if not choice_factors and "jet" in row.title.lower():
        choice_factors = [
            {"name": "aircraft_type", "label": "Aircraft Type", "type": "text"},
            {"name": "includes_catering", "label": "Includes Catering?", "type": "boolean"},
            {"name": "availability", "label": "Availability Confirmed", "type": "boolean"},
        ]
    
    return QuoteFormData(
        row_id=row.id,
        row_title=row.title,
        buyer_request=row.title,  # Could be more detailed
        choice_factors=choice_factors,
        seller_email=quote.seller_email,
        seller_company=quote.seller_company,
        expires_at=quote.token_expires_at.isoformat() if quote.token_expires_at else None,
    )


@router.post("/submit/{token}", response_model=QuoteResponse)
async def submit_quote(
    token: str,
    submission: QuoteSubmission,
    session=Depends(get_session),
):
    """
    Submit a quote via magic link.
    Creates a Bid from the quote.
    """
    # Find the seller quote by token
    result = await session.execute(
        select(SellerQuote).where(SellerQuote.token == token)
    )
    quote = result.scalar_one_or_none()
    
    if not quote:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    # Check expiration
    if quote.token_expires_at and quote.token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This link has expired")
    
    # Check if already submitted
    if quote.status == "submitted":
        raise HTTPException(status_code=400, detail="Quote already submitted")
    
    # Update quote with submission data
    quote.price = submission.price
    quote.currency = submission.currency
    quote.description = submission.description
    quote.status = "submitted"
    quote.submitted_at = datetime.utcnow()
    
    # Update contact info if provided
    if submission.contact_name:
        quote.seller_name = submission.contact_name
    if submission.contact_phone:
        quote.seller_phone = submission.contact_phone
    
    # Store answers as JSON
    import json
    answers = submission.answers or {}
    if submission.aircraft_type:
        answers["aircraft_type"] = submission.aircraft_type
    if submission.includes_catering is not None:
        answers["includes_catering"] = submission.includes_catering
    quote.answers = json.dumps(answers)
    
    # Create a Bid from the quote
    bid = Bid(
        row_id=quote.row_id,
        price=submission.price,
        shipping_cost=0.0,
        total_cost=submission.price,
        currency=submission.currency,
        item_title=f"Quote from {quote.seller_company or quote.seller_name}",
        item_url=None,
        image_url=None,
        source="seller_quote",
        condition="service",
        # Store provenance linking to quote
        provenance=json.dumps({
            "type": "seller_quote",
            "quote_id": quote.id,
            "seller_company": quote.seller_company,
            "seller_email": quote.seller_email,
            "description": submission.description,
            "answers": answers,
        }),
    )
    session.add(bid)
    await session.flush()  # Get bid.id
    
    # Link bid to quote
    quote.bid_id = bid.id
    
    # Update outreach event
    result = await session.execute(
        select(OutreachEvent).where(OutreachEvent.quote_token == token)
    )
    event = result.scalar_one_or_none()
    if event:
        event.quote_submitted_at = datetime.utcnow()
    
    await session.commit()

    # Look up row title for admin alert context
    row_result = await session.execute(select(Row).where(Row.id == quote.row_id))
    row_for_alert = row_result.scalar_one_or_none()

    await send_admin_vendor_alert(
        event_type="quote_submitted",
        vendor_name=quote.seller_name,
        vendor_email=quote.seller_email,
        vendor_company=quote.seller_company,
        row_title=row_for_alert.title if row_for_alert else None,
        row_id=quote.row_id,
        quote_price=submission.price,
        quote_description=submission.description,
    )
    
    return QuoteResponse(
        quote_id=quote.id,
        status="submitted",
        message="Quote submitted successfully! The buyer will be notified.",
    )


@router.get("/{quote_id}")
async def get_quote(quote_id: int, session=Depends(get_session)):
    """Get a quote by ID."""
    result = await session.execute(
        select(SellerQuote).where(SellerQuote.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {
        "id": quote.id,
        "row_id": quote.row_id,
        "seller_email": quote.seller_email,
        "seller_name": quote.seller_name,
        "seller_company": quote.seller_company,
        "price": quote.price,
        "currency": quote.currency,
        "description": quote.description,
        "status": quote.status,
        "submitted_at": quote.submitted_at,
    }


@router.post("/{quote_id}/select")
async def select_quote(
    quote_id: int,
    buyer_name: Optional[str] = None,
    buyer_phone: Optional[str] = None,
    session=Depends(get_session),
):
    """
    Buyer selects a quote - triggers email handoff.
    """
    # Get quote
    result = await session.execute(
        select(SellerQuote).where(SellerQuote.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if quote.status != "submitted":
        raise HTTPException(status_code=400, detail="Quote not yet submitted")
    
    # Get row for buyer info
    result = await session.execute(select(Row).where(Row.id == quote.row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Get buyer user
    result = await session.execute(select(User).where(User.id == row.user_id))
    buyer = result.scalar_one_or_none()
    
    buyer_email = buyer.email if buyer else "demo@buyanything.ai"
    
    # Update quote status
    quote.status = "accepted"
    
    # Create deal handoff
    from models import generate_magic_link_token, Bid
    
    vendor_id = None
    if quote.bid_id:
        b_result = await session.execute(select(Bid).where(Bid.id == quote.bid_id))
        bid = b_result.scalar_one_or_none()
        if bid:
            vendor_id = bid.vendor_id
            bid.closing_status = "selected"
            session.add(bid)

    handoff = DealHandoff(
        row_id=quote.row_id,
        quote_id=quote.id,
        bid_id=quote.bid_id,
        vendor_id=vendor_id,
        buyer_user_id=buyer.id if buyer else 1,
        buyer_email=buyer_email,
        buyer_name=buyer_name,
        buyer_phone=buyer_phone,
        vendor_email=quote.seller_email,
        vendor_name=quote.seller_name,
        deal_value=quote.price,
        currency=quote.currency,
        status="introduced",
        acceptance_token=generate_magic_link_token(),
    )
    session.add(handoff)
    
    # Update row status
    row.status = "selected"
    
    await session.commit()
    await session.refresh(handoff)
    
    # Send handoff emails
    description = quote.description or ""
    if quote.answers:
        answers = safe_json_loads(quote.answers, {})
        if answers.get("aircraft_type"):
            description = f"Aircraft: {answers['aircraft_type']}. {description}"
    
    # Email to buyer
    buyer_result = await send_handoff_buyer_email(
        buyer_email=buyer_email,
        buyer_name=buyer_name,
        seller_name=quote.seller_name or "Sales Team",
        seller_company=quote.seller_company or "Vendor",
        seller_email=quote.seller_email,
        seller_phone=quote.seller_phone,
        request_summary=row.title,
        quote_price=quote.price,
        quote_description=description,
    )
    if buyer_result.success:
        handoff.buyer_email_sent_at = datetime.utcnow()
    
    # Email to seller
    seller_result = await send_handoff_seller_email(
        seller_email=quote.seller_email,
        seller_name=quote.seller_name,
        seller_company=quote.seller_company or "Vendor",
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        request_summary=row.title,
        quote_price=quote.price,
    )
    if seller_result.success:
        handoff.seller_email_sent_at = datetime.utcnow()
    
    await session.commit()
    
    return {
        "status": "success",
        "message": "Quote selected! Introduction emails sent.",
        "handoff_id": handoff.id,
        "deal_value": quote.price,
        "seller_company": quote.seller_company,
        "seller_email": quote.seller_email,
        "emails_sent": {
            "buyer": buyer_result.success,
            "seller": seller_result.success,
        },
    }


@router.patch("/handoffs/{handoff_id}/close")
async def close_handoff(
    handoff_id: int,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Mark a deal handoff as closed (deal completed).
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await session.execute(
        select(DealHandoff).where(DealHandoff.id == handoff_id)
    )
    handoff = result.scalar_one_or_none()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")

    if handoff.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to close this handoff")

    if handoff.status == "closed":
        return {"status": "already_closed", "handoff_id": handoff_id}

    handoff.status = "closed"
    handoff.closed_at = datetime.utcnow()
    await session.commit()

    return {
        "status": "closed",
        "handoff_id": handoff_id,
        "closed_at": handoff.closed_at.isoformat(),
    }
