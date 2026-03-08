"""Deal Pipeline API routes: deal CRUD, messaging, and state transitions."""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models.deals import Deal, DealMessage
from models import Row, Bid, Vendor
from services.deal_pipeline import (
    create_deal,
    record_message,
    relay_email,
    send_initial_outreach,
    transition_deal_status,
    resolve_deal_from_alias,
    identify_sender,
    MESSAGES_DOMAIN,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deals", tags=["deals"])


# ── Request / Response Models ────────────────────────────────────────────────


class DealCreateRequest(BaseModel):
    row_id: int
    bid_id: Optional[int] = None
    vendor_id: Optional[int] = None


class DealTransitionRequest(BaseModel):
    new_status: str
    vendor_quoted_price: Optional[float] = None
    agreed_terms_summary: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None


class DealResponse(BaseModel):
    id: int
    row_id: int
    bid_id: Optional[int]
    vendor_id: Optional[int]
    buyer_user_id: int
    status: str
    proxy_email: str
    vendor_quoted_price: Optional[float]
    platform_fee_pct: float
    platform_fee_amount: Optional[float]
    buyer_total: Optional[float]
    currency: str
    agreed_terms_summary: Optional[str]
    agreement_source: Optional[str] = None
    created_at: str
    updated_at: Optional[str]
    terms_agreed_at: Optional[str]
    funded_at: Optional[str]
    completed_at: Optional[str]


class MessageResponse(BaseModel):
    id: int
    deal_id: int
    sender_type: str
    sender_email: Optional[str]
    subject: Optional[str]
    content_text: str
    ai_classification: Optional[str]
    ai_confidence: Optional[float]
    created_at: str


def _deal_to_response(deal: Deal) -> dict:
    return {
        "id": deal.id,
        "row_id": deal.row_id,
        "bid_id": deal.bid_id,
        "vendor_id": deal.vendor_id,
        "buyer_user_id": deal.buyer_user_id,
        "status": deal.status,
        "proxy_email": f"{deal.proxy_email_alias}@{MESSAGES_DOMAIN}",
        "vendor_quoted_price": deal.vendor_quoted_price,
        "platform_fee_pct": deal.platform_fee_pct,
        "platform_fee_amount": deal.platform_fee_amount,
        "buyer_total": deal.buyer_total,
        "currency": deal.currency,
        "agreed_terms_summary": deal.agreed_terms_summary,
        "agreement_source": None,
        "created_at": deal.created_at.isoformat() if deal.created_at else None,
        "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
        "terms_agreed_at": deal.terms_agreed_at.isoformat() if deal.terms_agreed_at else None,
        "funded_at": deal.funded_at.isoformat() if deal.funded_at else None,
        "completed_at": deal.completed_at.isoformat() if deal.completed_at else None,
    }


def _msg_to_response(msg: DealMessage) -> dict:
    return {
        "id": msg.id,
        "deal_id": msg.deal_id,
        "sender_type": msg.sender_type,
        "sender_email": msg.sender_email,
        "subject": msg.subject,
        "content_text": msg.content_text,
        "ai_classification": msg.ai_classification,
        "ai_confidence": msg.ai_confidence,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("")
async def create_new_deal(
    request: DealCreateRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Create a new deal and send initial outreach to the vendor."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        deal = await create_deal(
            session=session,
            row_id=request.row_id,
            buyer_user_id=auth_session.user_id,
            bid_id=request.bid_id,
            vendor_id=request.vendor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Send initial outreach email
    row = await session.get(Row, request.row_id)
    request_summary = row.title if row else "Quote Request"
    email_result = await send_initial_outreach(deal, session, request_summary)

    # Record the outreach as a system message
    await record_message(
        session=session,
        deal_id=deal.id,
        sender_type="system",
        content_text=f"Deal initiated. Initial outreach sent to vendor. Subject: Quote Request: {request_summary}",
        subject=f"Quote Request: {request_summary}",
    )

    return {
        "deal": _deal_to_response(deal),
        "email_sent": email_result.success,
        "email_error": email_result.error,
    }


@router.get("")
async def list_deals(
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """List all deals for the authenticated user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    query = select(Deal).where(Deal.buyer_user_id == auth_session.user_id)
    if status:
        query = query.where(Deal.status == status)
    query = query.order_by(Deal.created_at.desc())

    result = await session.execute(query)
    deals = result.scalars().all()

    return {"deals": [_deal_to_response(d) for d in deals]}


@router.get("/{deal_id}")
async def get_deal(
    deal_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get a single deal with its messages."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    deal = await session.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Fetch messages
    msg_result = await session.execute(
        select(DealMessage)
        .where(DealMessage.deal_id == deal_id)
        .order_by(DealMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()

    # Fetch vendor info
    vendor_info = None
    if deal.vendor_id:
        vendor = await session.get(Vendor, deal.vendor_id)
        if vendor:
            vendor_info = {
                "id": vendor.id,
                "name": vendor.name,
                "email": vendor.email,
                "domain": vendor.domain,
            }

    return {
        "deal": _deal_to_response(deal),
        "messages": [_msg_to_response(m) for m in messages],
        "vendor": vendor_info,
    }


@router.post("/{deal_id}/transition")
async def transition_deal(
    deal_id: int,
    request: DealTransitionRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Transition a deal to a new status."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    deal = await session.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    previous_status = deal.status

    try:
        deal = await transition_deal_status(
            session=session,
            deal=deal,
            new_status=request.new_status,
            vendor_quoted_price=request.vendor_quoted_price,
            agreed_terms_summary=request.agreed_terms_summary,
            stripe_payment_intent_id=request.stripe_payment_intent_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Record system message for the transition
    transition_source = None
    if request.new_status == "terms_agreed":
        transition_source = "manual"
    elif request.new_status == "negotiating" and previous_status == "terms_agreed":
        transition_source = "manual_reopen"

    message_text = f"Deal status changed to {request.new_status}."
    if transition_source:
        message_text = f"Deal status changed to {request.new_status} (source: {transition_source})."

    await record_message(
        session=session,
        deal_id=deal.id,
        sender_type="system",
        content_text=message_text,
    )

    return {"deal": _deal_to_response(deal)}


@router.get("/{deal_id}/messages")
async def get_deal_messages(
    deal_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get all messages for a deal."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    deal = await session.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await session.execute(
        select(DealMessage)
        .where(DealMessage.deal_id == deal_id)
        .order_by(DealMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return {"messages": [_msg_to_response(m) for m in messages]}


# ── Retired Endpoints ────────────────────────────────────────────────────────


@router.post("/{deal_id}/fund")
async def fund_deal_retired(
    deal_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    raise HTTPException(
        status_code=410,
        detail="Deal funding is retired. BuyAnything is an introduction platform; handle payment directly with the vendor.",
    )


@router.post("/{deal_id}/release")
async def release_deal_payout(
    deal_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Confirm delivery and release vendor payout.
    Called by the buyer after they confirm the service/goods were received.
    For Stripe Connect deals, the transfer happens automatically via transfer_data.
    This endpoint just transitions the deal to completed.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    deal = await session.get(Deal, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if deal.status not in ("funded", "in_transit"):
        raise HTTPException(
            status_code=400,
            detail=f"Deal must be funded or in_transit to release (current: {deal.status})",
        )

    try:
        deal = await transition_deal_status(
            session=session,
            deal=deal,
            new_status="completed",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await record_message(
        session=session,
        deal_id=deal.id,
        sender_type="system",
        content_text="Buyer confirmed delivery. Vendor payout initiated.",
    )

    return {"deal": _deal_to_response(deal)}
