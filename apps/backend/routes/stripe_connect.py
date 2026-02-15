"""Stripe Connect onboarding routes (PRD 00 — Revenue & Monetization).

Enables merchants to connect their Stripe account so the platform can collect
application_fee_amount on checkout sessions.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Vendor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stripe-connect", tags=["stripe_connect"])

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


class OnboardingResponse(BaseModel):
    onboarding_url: str
    account_id: str


class EarningsSummary(BaseModel):
    total_earnings: float
    pending_payouts: float
    completed_transactions: int
    commission_rate: float


@router.post("/onboard", response_model=OnboardingResponse)
async def start_onboarding(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a Stripe Connect account for the merchant and return an onboarding URL.
    If the merchant already has an account, returns a new account link for re-onboarding.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Find merchant for this user
    result = await session.exec(
        select(Merchant).where(Merchant.user_id == auth_session.user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(
            status_code=403,
            detail="No merchant profile found. Register at /merchants/register first.",
        )

    stripe = _get_stripe()
    app_base = os.getenv("APP_BASE_URL", "http://localhost:3003")

    # Create or reuse Stripe Connected Account
    if not merchant.stripe_account_id:
        try:
            account = stripe.Account.create(
                type="express",
                email=merchant.email,
                business_profile={"name": merchant.business_name},
                metadata={"merchant_id": str(merchant.id)},
            )
            merchant.stripe_account_id = account.id
            session.add(merchant)
            await session.commit()
        except Exception as e:
            logger.error(f"[STRIPE CONNECT] Account creation failed: {e}")
            raise HTTPException(status_code=502, detail="Failed to create Stripe account")

    # Generate onboarding link
    try:
        account_link = stripe.AccountLink.create(
            account=merchant.stripe_account_id,
            refresh_url=f"{app_base}/seller/stripe-connect?refresh=1",
            return_url=f"{app_base}/seller/stripe-connect?success=1",
            type="account_onboarding",
        )
    except Exception as e:
        logger.error(f"[STRIPE CONNECT] Account link creation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to create onboarding link")

    return OnboardingResponse(
        onboarding_url=account_link.url,
        account_id=merchant.stripe_account_id,
    )


@router.get("/status")
async def onboarding_status(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Check the merchant's Stripe Connect onboarding status."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Merchant).where(Merchant.user_id == auth_session.user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(status_code=403, detail="No merchant profile")

    if not merchant.stripe_account_id:
        return {
            "connected": False,
            "onboarding_complete": False,
            "account_id": None,
        }

    # Check account status with Stripe
    stripe = _get_stripe()
    try:
        account = stripe.Account.retrieve(merchant.stripe_account_id)
        charges_enabled = account.charges_enabled
        details_submitted = account.details_submitted

        # Update local record if onboarding is now complete
        if charges_enabled and not merchant.stripe_onboarding_complete:
            merchant.stripe_onboarding_complete = True
            session.add(merchant)
            await session.commit()

        return {
            "connected": True,
            "onboarding_complete": charges_enabled and details_submitted,
            "charges_enabled": charges_enabled,
            "details_submitted": details_submitted,
            "account_id": merchant.stripe_account_id,
        }
    except Exception as e:
        logger.error(f"[STRIPE CONNECT] Status check failed: {e}")
        return {
            "connected": True,
            "onboarding_complete": merchant.stripe_onboarding_complete,
            "account_id": merchant.stripe_account_id,
            "error": "Could not verify with Stripe",
        }


@router.get("/earnings", response_model=EarningsSummary)
async def seller_earnings(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get the seller's earnings summary (PRD 00)."""
    from sqlalchemy import func
    from models import PurchaseEvent, Bid

    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Vendor).where(Vendor.user_id == auth_session.user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(status_code=403, detail="No merchant profile")

    # Find purchases for bids linked to this vendor
    purchases_result = await session.exec(
        select(
            func.count(PurchaseEvent.id),
            func.coalesce(func.sum(PurchaseEvent.amount), 0),
            func.coalesce(func.sum(PurchaseEvent.platform_fee_amount), 0),
        ).where(
            PurchaseEvent.bid_id.in_(
                select(Bid.id).where(Bid.vendor_id == merchant.id)
            ),
            PurchaseEvent.status == "completed",
        )
    )
    row = purchases_result.one()
    txn_count, total_amount, total_fees = row

    return EarningsSummary(
        total_earnings=round(float(total_amount) - float(total_fees), 2),
        pending_payouts=0.0,  # Would come from Stripe Balance API in production
        completed_transactions=txn_count,
        commission_rate=merchant.default_commission_rate,
    )
