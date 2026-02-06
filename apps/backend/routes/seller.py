"""Seller dashboard routes — inbox, quotes, profile management."""
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import (
    Bid,
    Merchant,
    Row,
    SellerQuote,
    User,
    generate_magic_link_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller", tags=["seller"])


# ── Response models ──────────────────────────────────────────────────────


class RFPSummary(BaseModel):
    row_id: int
    title: str
    status: Optional[str] = None
    service_category: Optional[str] = None
    choice_factors: Optional[str] = None
    created_at: Optional[datetime] = None
    quote_count: int = 0


class QuoteSummary(BaseModel):
    id: int
    row_id: int
    row_title: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    status: str = "pending"
    created_at: Optional[datetime] = None


class MerchantProfile(BaseModel):
    id: int
    business_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    categories: Optional[str] = None
    service_areas: Optional[str] = None
    website: Optional[str] = None


class MerchantProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    categories: Optional[str] = None
    service_areas: Optional[str] = None
    website: Optional[str] = None


class SellerQuoteCreate(BaseModel):
    row_id: int
    price: Optional[float] = None
    description: Optional[str] = None
    choice_answers: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────


async def _get_merchant(session: AsyncSession, user_id: int) -> Merchant:
    """Get the merchant record for a user, or raise 403."""
    result = await session.exec(
        select(Merchant).where(Merchant.user_id == user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(
            status_code=403,
            detail="No merchant profile found. Register at /merchants/register first.",
        )
    return merchant


# ── Inbox ────────────────────────────────────────────────────────────────


@router.get("/inbox", response_model=List[RFPSummary])
async def seller_inbox(
    page: int = 1,
    per_page: int = 20,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get buyer RFPs matching the seller's registered categories."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    merchant = await _get_merchant(session, auth_session.user_id)

    # Parse merchant categories
    categories: List[str] = []
    if merchant.categories:
        try:
            parsed = json.loads(merchant.categories)
            if isinstance(parsed, list):
                categories = [str(c).strip().lower() for c in parsed if c]
            elif isinstance(parsed, str):
                categories = [parsed.strip().lower()]
        except (json.JSONDecodeError, TypeError):
            categories = [merchant.categories.strip().lower()]

    # Build query for matching rows
    query = select(Row).where(
        Row.is_service == True,
        Row.status.in_(["sourcing", "inviting", "bids_arriving", "open"]),
    )

    # Filter by category if merchant has categories
    if categories:
        category_filters = []
        for cat in categories:
            category_filters.append(Row.service_category.ilike(f"%{cat}%"))
            category_filters.append(Row.title.ilike(f"%{cat}%"))
        query = query.where(or_(*category_filters))

    query = (
        query.order_by(Row.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await session.exec(query)
    rows = result.all()

    if not rows:
        return []

    # Batch fetch quote counts in a single query
    row_ids = [r.id for r in rows]
    quote_counts_result = await session.exec(
        select(SellerQuote.row_id, func.count(SellerQuote.id).label("cnt"))
        .where(SellerQuote.row_id.in_(row_ids))
        .group_by(SellerQuote.row_id)
    )
    quote_counts = {row_id: cnt for row_id, cnt in quote_counts_result}

    summaries: List[RFPSummary] = [
        RFPSummary(
            row_id=row.id,
            title=row.title,
            status=row.status,
            service_category=row.service_category,
            choice_factors=row.choice_factors,
            created_at=row.created_at,
            quote_count=quote_counts.get(row.id, 0),
        )
        for row in rows
    ]

    return summaries


# ── Quotes ───────────────────────────────────────────────────────────────


@router.get("/quotes", response_model=List[QuoteSummary])
async def seller_quotes(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get all quotes submitted by this seller."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    merchant = await _get_merchant(session, auth_session.user_id)

    # Find quotes by merchant email
    quotes_result = await session.exec(
        select(SellerQuote)
        .where(SellerQuote.seller_email == merchant.email)
        .order_by(SellerQuote.created_at.desc())
    )
    quotes = quotes_result.all()

    if not quotes:
        return []

    # Batch fetch row titles in a single query
    quote_row_ids = list({q.row_id for q in quotes if q.row_id})
    if quote_row_ids:
        rows_result = await session.exec(
            select(Row.id, Row.title).where(Row.id.in_(quote_row_ids))
        )
        row_titles = {row_id: title for row_id, title in rows_result}
    else:
        row_titles = {}

    summaries: List[QuoteSummary] = [
        QuoteSummary(
            id=q.id,
            row_id=q.row_id,
            row_title=row_titles.get(q.row_id),
            price=q.price,
            description=q.description,
            status=q.status or "pending",
            created_at=q.created_at,
        )
        for q in quotes
    ]

    return summaries


@router.post("/quotes", response_model=QuoteSummary)
async def submit_quote(
    body: SellerQuoteCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Submit a quote for a buyer RFP (authenticated, no magic link needed)."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    merchant = await _get_merchant(session, auth_session.user_id)

    # Verify row exists
    row = await session.get(Row, body.row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Create quote
    token = generate_magic_link_token()
    quote = SellerQuote(
        row_id=body.row_id,
        seller_name=merchant.contact_name or merchant.business_name,
        seller_email=merchant.email,
        seller_company=merchant.business_name,
        token=token,
        price=body.price,
        description=body.description,
        choice_answers=body.choice_answers,
        status="submitted",
    )
    session.add(quote)
    await session.commit()
    await session.refresh(quote)

    # Convert to bid so it appears in the buyer's tile view
    bid = Bid(
        row_id=body.row_id,
        price=body.price or 0.0,
        currency="USD",
        item_title=f"Quote from {merchant.business_name}",
        item_url=f"mailto:{merchant.email}",
        source="seller_quote",
        is_selected=False,
    )
    session.add(bid)
    await session.commit()

    return QuoteSummary(
        id=quote.id,
        row_id=quote.row_id,
        row_title=row.title,
        price=quote.price,
        description=quote.description,
        status=quote.status or "submitted",
        created_at=quote.created_at,
    )


# ── Profile ──────────────────────────────────────────────────────────────


@router.get("/profile", response_model=MerchantProfile)
async def get_profile(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get the current seller's merchant profile."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    merchant = await _get_merchant(session, auth_session.user_id)

    return MerchantProfile(
        id=merchant.id,
        business_name=merchant.business_name,
        contact_name=merchant.contact_name,
        email=merchant.email,
        phone=merchant.phone,
        categories=merchant.categories,
        service_areas=merchant.service_areas,
        website=merchant.website,
    )


@router.patch("/profile", response_model=MerchantProfile)
async def update_profile(
    body: MerchantProfileUpdate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Update the current seller's merchant profile."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    merchant = await _get_merchant(session, auth_session.user_id)

    update_data = body.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(merchant, field_name, value)

    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)

    return MerchantProfile(
        id=merchant.id,
        business_name=merchant.business_name,
        contact_name=merchant.contact_name,
        email=merchant.email,
        phone=merchant.phone,
        categories=merchant.categories,
        service_areas=merchant.service_areas,
        website=merchant.website,
    )
