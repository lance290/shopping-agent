"""Brand portal routes for CPG coupon submission (PRD-08).

Provides:
  - GET  /brands/claim?token=XYZ  — verify token, return campaign info
  - POST /brands/claim             — submit coupon details (creates PopSwap)
  - POST /brands/campaigns         — admin: create campaign + generate magic link
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.coupons import (
    PopSwap,
    CouponCampaign,
    BrandPortalToken,
)

logger = logging.getLogger(__name__)
brand_portal_router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CampaignCreateBody(BaseModel):
    brand_name: str
    brand_contact_email: Optional[str] = None
    category: str
    target_product: Optional[str] = None
    intent_count: int = 0


class CouponSubmitBody(BaseModel):
    token: str
    swap_product_name: str
    savings_cents: int
    offer_description: Optional[str] = None
    swap_product_url: Optional[str] = None
    swap_product_image: Optional[str] = None
    offer_type: str = "coupon"
    terms: Optional[str] = None


# ---------------------------------------------------------------------------
# Brand Portal Endpoints
# ---------------------------------------------------------------------------


@brand_portal_router.get("/brands/claim")
async def verify_brand_token(
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Verify a brand portal magic link token and return campaign info."""
    stmt = select(BrandPortalToken).where(BrandPortalToken.token == token)
    result = await session.execute(stmt)
    portal_token = result.scalar_one_or_none()

    if not portal_token:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    if portal_token.is_used:
        raise HTTPException(status_code=410, detail="Token already used")

    if portal_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")

    campaign = await session.get(CouponCampaign, portal_token.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "valid": True,
        "campaign": {
            "id": campaign.id,
            "brand_name": campaign.brand_name,
            "category": campaign.category,
            "target_product": campaign.target_product,
            "intent_count": campaign.intent_count,
        },
    }


@brand_portal_router.post("/brands/claim")
async def submit_brand_coupon(
    body: CouponSubmitBody,
    session: AsyncSession = Depends(get_session),
):
    """Brand PM submits a coupon via the portal. Creates a PopSwap."""
    stmt = select(BrandPortalToken).where(BrandPortalToken.token == body.token)
    result = await session.execute(stmt)
    portal_token = result.scalar_one_or_none()

    if not portal_token:
        raise HTTPException(status_code=404, detail="Invalid token")

    if portal_token.is_used:
        raise HTTPException(status_code=410, detail="Token already used")

    if portal_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")

    campaign = await session.get(CouponCampaign, portal_token.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if body.savings_cents <= 0:
        raise HTTPException(status_code=400, detail="Savings must be positive")

    # Create the PopSwap offer
    swap = PopSwap(
        category=campaign.category,
        target_product=campaign.target_product,
        swap_product_name=body.swap_product_name.strip(),
        swap_product_image=body.swap_product_image,
        swap_product_url=body.swap_product_url,
        offer_type=body.offer_type,
        savings_cents=body.savings_cents,
        offer_description=body.offer_description,
        terms=body.terms,
        brand_name=campaign.brand_name,
        brand_contact_email=campaign.brand_contact_email,
        provider="homebrew",
        is_active=True,
    )
    session.add(swap)
    await session.flush()

    # Mark token as used and link campaign to the new swap
    portal_token.is_used = True
    session.add(portal_token)

    campaign.status = "claimed"
    campaign.swap_id = swap.id
    campaign.updated_at = datetime.utcnow()
    session.add(campaign)

    await session.commit()
    await session.refresh(swap)

    logger.info(
        f"[BrandPortal] Campaign #{campaign.id} claimed: "
        f"{swap.swap_product_name} ({swap.brand_name}) — "
        f"${swap.savings_cents / 100:.2f} off"
    )

    return {
        "success": True,
        "swap_id": swap.id,
        "swap_product_name": swap.swap_product_name,
        "savings_display": f"${swap.savings_cents / 100:.2f}",
    }


# ---------------------------------------------------------------------------
# Admin: Campaign Management
# ---------------------------------------------------------------------------


@brand_portal_router.post("/brands/campaigns")
async def create_campaign(
    body: CampaignCreateBody,
    session: AsyncSession = Depends(get_session),
):
    """Admin: create a coupon campaign and generate a magic link for the brand PM."""
    campaign = CouponCampaign(
        brand_name=body.brand_name.strip(),
        brand_contact_email=body.brand_contact_email,
        category=body.category.strip().lower(),
        target_product=body.target_product,
        intent_count=body.intent_count,
        status="pending",
    )
    session.add(campaign)
    await session.flush()

    portal_token = BrandPortalToken(
        campaign_id=campaign.id,
        brand_email=body.brand_contact_email,
    )
    session.add(portal_token)
    await session.commit()
    await session.refresh(campaign)
    await session.refresh(portal_token)

    portal_url = f"https://popsavings.com/brands/claim?token={portal_token.token}"

    logger.info(
        f"[BrandPortal] Campaign #{campaign.id} created for {campaign.brand_name} "
        f"({campaign.category}). Portal URL generated."
    )

    return {
        "campaign_id": campaign.id,
        "brand_name": campaign.brand_name,
        "category": campaign.category,
        "portal_url": portal_url,
        "token": portal_token.token,
        "expires_at": portal_token.expires_at.isoformat(),
    }
