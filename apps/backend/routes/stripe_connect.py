"""Stripe Connect onboarding routes (PRD 00 — Revenue & Monetization).

Enables merchants to connect their Stripe account so the platform can collect
application_fee_amount on checkout sessions.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Vendor

Merchant = Vendor  # Unified model — Merchant is an alias for Vendor

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
    request: Request,
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
    from routes.checkout import _get_app_base
    app_base = _get_app_base(request)

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


class OnboardVendorRequest(BaseModel):
    vendor_id: int


@router.post("/onboard-vendor")
async def onboard_vendor_direct(
    body: OnboardVendorRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Create or reuse a Stripe Express Connected Account for any Vendor by ID.
    Does NOT require the vendor to have a Merchant/user profile — works for
    EA-sourced vendors discovered through search or outreach.
    Returns a Stripe-hosted onboarding URL the EA can share with the vendor.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vendor = await session.get(Vendor, body.vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    stripe = _get_stripe()
    from routes.checkout import _get_app_base
    app_base = _get_app_base(request)

    if not vendor.stripe_account_id:
        if not vendor.email:
            raise HTTPException(
                status_code=400,
                detail="Vendor has no email on file — cannot create Stripe account",
            )
        try:
            account = stripe.Account.create(
                type="express",
                email=vendor.email,
                business_profile={"name": vendor.name},
                metadata={"vendor_id": str(vendor.id)},
            )
            vendor.stripe_account_id = account.id
            session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
        except Exception as e:
            logger.error(f"[STRIPE CONNECT] Vendor account creation failed: {e}")
            raise HTTPException(status_code=502, detail="Failed to create Stripe account")

    try:
        account_link = stripe.AccountLink.create(
            account=vendor.stripe_account_id,
            refresh_url=f"{app_base}/seller?tab=profile&stripe=refresh",
            return_url=f"{app_base}/seller?tab=profile&stripe=complete",
            type="account_onboarding",
        )
    except Exception as e:
        logger.error(f"[STRIPE CONNECT] Vendor onboarding link failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to create onboarding link")

    return {
        "onboarding_url": account_link.url,
        "stripe_account_id": vendor.stripe_account_id,
        "vendor_id": vendor.id,
        "vendor_email": vendor.email,
    }


@router.post("/webhook")
async def stripe_connect_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Handle Stripe Connect webhooks — primarily account.updated.
    Syncs vendor onboarding status automatically when Stripe fires events.
    """
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    connect_webhook_secret = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "")

    if connect_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, connect_webhook_secret)
        except Exception as e:
            logger.warning(f"[STRIPE CONNECT WEBHOOK] Signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)
        logger.warning("[STRIPE CONNECT WEBHOOK] No webhook secret configured — skipping signature verification")

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data_object = (event.get("data", {}).get("object", {}) if isinstance(event, dict)
                   else event.data.object)

    if event_type == "account.updated":
        account_id = data_object.get("id") if isinstance(data_object, dict) else data_object.id
        charges_enabled = (data_object.get("charges_enabled") if isinstance(data_object, dict)
                           else data_object.charges_enabled)

        if not account_id:
            return {"status": "ignored", "reason": "no_account_id"}

        result = await session.exec(
            select(Vendor).where(Vendor.stripe_account_id == account_id)
        )
        vendor = result.first()
        if not vendor:
            logger.info(f"[STRIPE CONNECT WEBHOOK] No vendor for account {account_id}")
            return {"status": "ignored", "reason": "unknown_account"}

        changed = False
        if charges_enabled and not vendor.stripe_onboarding_complete:
            vendor.stripe_onboarding_complete = True
            changed = True
        elif not charges_enabled and vendor.stripe_onboarding_complete:
            vendor.stripe_onboarding_complete = False
            changed = True

        if changed:
            session.add(vendor)
            await session.commit()
            logger.info(
                f"[STRIPE CONNECT WEBHOOK] Vendor {vendor.id} onboarding_complete={vendor.stripe_onboarding_complete}"
            )

        return {"status": "processed", "vendor_id": vendor.id, "charges_enabled": charges_enabled}

    return {"status": "ignored", "event_type": event_type}


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
