"""
Merchant Registry API routes.
Self-registration for preferred seller network.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Merchant, Seller
from database import get_session
from dependencies import get_current_session

router = APIRouter(prefix="/merchants", tags=["merchants"])


class MerchantRegistration(BaseModel):
    business_name: str
    contact_name: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    categories: list[str] = []
    service_areas: list[str] = []


class MerchantResponse(BaseModel):
    id: int
    business_name: str
    contact_name: str
    email: str
    phone: Optional[str]
    website: Optional[str]
    categories: list[str]
    service_areas: list[str]
    status: str
    created_at: str


@router.post("/register")
async def register_merchant(
    registration: MerchantRegistration,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Register a new merchant in the preferred seller network.
    Requires authentication so the merchant is linked to the user account.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Login required to register as a seller")

    # Check if user already has a merchant profile
    existing_user = await session.execute(
        select(Merchant).where(Merchant.user_id == auth_session.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have a merchant profile."
        )

    # Check for duplicate email
    result = await session.execute(
        select(Merchant).where(Merchant.email == registration.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A merchant with this email is already registered."
        )

    # Create or find Seller record for bid attribution
    seller_result = await session.execute(
        select(Seller).where(Seller.name == registration.business_name)
    )
    seller = seller_result.scalar_one_or_none()
    if not seller:
        seller = Seller(
            name=registration.business_name,
            domain=registration.website or None,
        )
        session.add(seller)
        await session.flush()

    merchant = Merchant(
        business_name=registration.business_name,
        contact_name=registration.contact_name,
        email=registration.email,
        phone=registration.phone,
        website=registration.website,
        categories=json.dumps(registration.categories) if registration.categories else None,
        service_areas=json.dumps(registration.service_areas) if registration.service_areas else None,
        seller_id=seller.id,
        user_id=auth_session.user_id,
        status="pending",
    )
    session.add(merchant)
    await session.commit()
    await session.refresh(merchant)

    return {
        "status": "registered",
        "merchant_id": merchant.id,
        "message": "Registration received. You will be contacted for verification.",
    }


@router.get("/me")
async def get_my_merchant_profile(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get the merchant profile for the authenticated user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.execute(
        select(Merchant).where(Merchant.user_id == auth_session.user_id)
    )
    merchant = result.scalar_one_or_none()
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    categories = []
    if merchant.categories:
        try:
            categories = json.loads(merchant.categories)
        except (json.JSONDecodeError, TypeError):
            pass

    service_areas = []
    if merchant.service_areas:
        try:
            service_areas = json.loads(merchant.service_areas)
        except (json.JSONDecodeError, TypeError):
            pass

    return MerchantResponse(
        id=merchant.id,
        business_name=merchant.business_name,
        contact_name=merchant.contact_name,
        email=merchant.email,
        phone=merchant.phone,
        website=merchant.website,
        categories=categories,
        service_areas=service_areas,
        status=merchant.status,
        created_at=merchant.created_at.isoformat(),
    )


@router.get("/search")
async def search_merchants(
    category: Optional[str] = None,
    area: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Search verified merchants by category and/or service area.
    Used by the matching algorithm to prioritize registered merchants.
    """
    # TODO: Push category/area filtering to DB query (e.g. JSON contains or
    # a categories join table) once merchant volume justifies it.
    query = select(Merchant).where(Merchant.status == "verified")

    result = await session.execute(query)
    merchants = result.scalars().all()

    # Filter by category and area in Python (JSON fields)
    matched = []
    for m in merchants:
        cats = json.loads(m.categories) if m.categories else []
        areas = json.loads(m.service_areas) if m.service_areas else []

        if category and category not in cats:
            continue
        if area and area not in areas and "nationwide" not in areas:
            continue

        matched.append({
            "id": m.id,
            "business_name": m.business_name,
            "contact_name": m.contact_name,
            "website": m.website,
            "categories": cats,
            "service_areas": areas,
        })

    return {"merchants": matched, "count": len(matched)}
