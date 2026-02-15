"""
Merchant Registry API routes.
Self-registration for preferred seller network.
"""
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Vendor
from utils.json_utils import safe_json_loads

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
        service_areas=json.dumps(registration.service_areas) if registration.service_areas else None,
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
    service_areas = safe_json_loads(vendor.service_areas, [])

    return MerchantResponse(
        id=vendor.id,
        business_name=vendor.name,
        contact_name=vendor.contact_name or "",
        email=vendor.email or "",
        phone=vendor.phone,
        website=vendor.website,
        categories=categories,
        service_areas=service_areas,
        status=vendor.status,
        created_at=vendor.created_at.isoformat(),
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
    query = select(Vendor).where(Vendor.status == "verified")

    result = await session.execute(query)
    vendors = result.scalars().all()

    # Filter by category and area in Python
    matched = []
    for v in vendors:
        cats = [v.category] if v.category else []
        areas = safe_json_loads(v.service_areas, [])

        if category and category not in cats:
            continue
        if area and area not in areas and "nationwide" not in areas:
            continue

        matched.append({
            "id": v.id,
            "business_name": v.name,
            "contact_name": v.contact_name,
            "website": v.website,
            "categories": cats,
            "service_areas": areas,
        })

    return {"merchants": matched, "count": len(matched)}


# ── Stripe Connect Onboarding ─────────────────────────────────────────

# Lazy-init Stripe
_stripe = None

def _get_stripe():
    global _stripe
    if _stripe is None:
        try:
            import stripe as _stripe_mod
            _stripe_mod.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            _stripe = _stripe_mod
        except ImportError:
            raise HTTPException(status_code=503, detail="Stripe SDK not installed")
    if not _stripe.api_key:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not configured")
    return _stripe


@router.post("/connect/onboard")
async def start_stripe_connect_onboarding(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Start Stripe Connect onboarding for the authenticated merchant.
    Returns a Stripe-hosted onboarding URL.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Find merchant for this user
    result = await session.exec(
        select(Vendor).where(Vendor.user_id == auth_session.user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found. Register first.")

    stripe = _get_stripe()
    app_base = os.getenv("APP_BASE_URL", "http://localhost:3003")

    # Create or reuse Stripe Connect account
    if not merchant.stripe_account_id:
        try:
            account = stripe.Account.create(
                type="express",
                email=merchant.email,
                metadata={"merchant_id": str(merchant.id)},
            )
            merchant.stripe_account_id = account.id
            session.add(merchant)
            await session.commit()
            await session.refresh(merchant)
        except Exception as e:
            logger.error(f"[STRIPE CONNECT] Account creation failed: {e}")
            raise HTTPException(status_code=502, detail="Failed to create Stripe account")

    # Create onboarding link
    try:
        account_link = stripe.AccountLink.create(
            account=merchant.stripe_account_id,
            refresh_url=f"{app_base}/seller?tab=profile&stripe=refresh",
            return_url=f"{app_base}/seller?tab=profile&stripe=complete",
            type="account_onboarding",
        )
    except Exception as e:
        logger.error(f"[STRIPE CONNECT] Account link creation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to create onboarding link")

    return {"onboarding_url": account_link.url, "stripe_account_id": merchant.stripe_account_id}


@router.get("/connect/status")
async def stripe_connect_status(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Check Stripe Connect onboarding status for the authenticated merchant."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Vendor).where(Vendor.user_id == auth_session.user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    if not merchant.stripe_account_id:
        return {"connected": False, "onboarding_complete": False}

    # Check account status with Stripe
    stripe = _get_stripe()
    try:
        account = stripe.Account.retrieve(merchant.stripe_account_id)
        charges_enabled = account.charges_enabled
        details_submitted = account.details_submitted

        # Update local state if onboarding just completed
        if charges_enabled and not merchant.stripe_onboarding_complete:
            merchant.stripe_onboarding_complete = True
            session.add(merchant)
            await session.commit()

        return {
            "connected": True,
            "onboarding_complete": charges_enabled and details_submitted,
            "charges_enabled": charges_enabled,
            "stripe_account_id": merchant.stripe_account_id,
        }
    except Exception as e:
        logger.error(f"[STRIPE CONNECT] Status check failed: {e}")
        return {"connected": True, "onboarding_complete": merchant.stripe_onboarding_complete}
