"""
Merchant Registry API routes.
Self-registration for preferred seller network.
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Vendor

# Merchant is now an alias for Vendor
Merchant = Vendor
from database import get_session
from dependencies import get_current_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchants", tags=["merchants"])


class MerchantRegistration(BaseModel):
    business_name: str
    contact_name: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    categories: list[str] = []


class MerchantResponse(BaseModel):
    id: int
    business_name: str
    contact_name: str
    email: str
    phone: Optional[str]
    website: Optional[str]
    categories: list[str]
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

    # Check if user already has a vendor/merchant profile
    existing_user = await session.execute(
        select(Vendor).where(Vendor.user_id == auth_session.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have a merchant profile."
        )

    # Check for duplicate email
    result = await session.execute(
        select(Vendor).where(Vendor.email == registration.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A merchant with this email is already registered."
        )

    # Create unified Vendor record (replaces old Seller + Merchant pair)
    vendor = Vendor(
        name=registration.business_name,
        contact_name=registration.contact_name,
        email=registration.email,
        phone=registration.phone,
        website=registration.website,
        domain=registration.website or None,
        category=registration.categories[0] if registration.categories else None,
        user_id=auth_session.user_id,
        status="pending",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    return {
        "status": "registered",
        "merchant_id": vendor.id,
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
        select(Vendor).where(Vendor.user_id == auth_session.user_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    categories = [vendor.category] if vendor.category else []

    return MerchantResponse(
        id=vendor.id,
        business_name=vendor.name,
        contact_name=vendor.contact_name or "",
        email=vendor.email or "",
        phone=vendor.phone,
        website=vendor.website,
        categories=categories,
        status=vendor.status,
        created_at=vendor.created_at.isoformat(),
    )


@router.get("/search")
async def search_merchants(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Search verified merchants by category.
    Used by the matching algorithm to prioritize registered merchants.
    """
    query = select(Vendor).where(Vendor.status == "verified")

    result = await session.execute(query)
    vendors = result.scalars().all()

    matched = []
    for v in vendors:
        cats = [v.category] if v.category else []

        if category and category not in cats:
            continue

        matched.append({
            "id": v.id,
            "business_name": v.name,
            "contact_name": v.contact_name,
            "website": v.website,
            "categories": cats,
        })

    return {"merchants": matched, "count": len(matched)}


# ── Stripe Connect Onboarding (delegates to stripe_connect.py) ────────
# Kept as thin redirects for backward compatibility with existing frontend callers.


@router.post("/connect/onboard")
async def start_stripe_connect_onboarding(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Delegate to canonical /stripe-connect/onboard endpoint."""
    raise HTTPException(
        status_code=308,
        detail="Use POST /stripe-connect/onboard instead",
        headers={"Location": "/stripe-connect/onboard"},
    )


@router.get("/connect/status")
async def stripe_connect_status(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Delegate to canonical /stripe-connect/status endpoint."""
    raise HTTPException(
        status_code=308,
        detail="Use GET /stripe-connect/status instead",
        headers={"Location": "/stripe-connect/status"},
    )
