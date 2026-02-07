"""Checkout routes - Stripe Checkout Session creation and webhook handling."""
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Bid, Row, PurchaseEvent, Merchant, Seller
from audit import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(tags=["checkout"])

# Lazy-init Stripe to avoid import errors when key isn't set
_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is None:
        try:
            import stripe as _stripe_mod

            _stripe_mod.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            _stripe = _stripe_mod
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Stripe SDK not installed. Run: uv add stripe",
            )
    if not _stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="STRIPE_SECRET_KEY not configured",
        )
    return _stripe


# ── Request / Response models ────────────────────────────────────────────


class CheckoutCreateRequest(BaseModel):
    bid_id: int
    row_id: int
    success_url: str = ""
    cancel_url: str = ""


class CheckoutCreateResponse(BaseModel):
    checkout_url: str
    session_id: str


# ── Create Checkout Session ──────────────────────────────────────────────


@router.post("/api/checkout/create-session", response_model=CheckoutCreateResponse)
async def create_checkout_session(
    body: CheckoutCreateRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Create a Stripe Checkout Session for a bid."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stripe = _get_stripe()

    # Validate bid exists and belongs to user's row
    bid = await session.get(Bid, body.bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    row_result = await session.exec(
        select(Row).where(Row.id == body.row_id, Row.user_id == auth_session.user_id)
    )
    row = row_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found or access denied")

    if bid.row_id != row.id:
        raise HTTPException(status_code=400, detail="Bid does not belong to this row")

    # Don't allow checkout for service providers (no fixed price)
    if bid.price is None or bid.price <= 0:
        raise HTTPException(
            status_code=400, detail="Cannot checkout items without a price"
        )

    # Build line item
    unit_amount = int(round(bid.price * 100))  # Stripe uses cents
    currency = (bid.currency or "USD").lower()

    line_item = {
        "price_data": {
            "currency": currency,
            "unit_amount": unit_amount,
            "product_data": {
                "name": bid.item_title or "Purchase",
            },
        },
        "quantity": 1,
    }

    # Add image if available
    if bid.image_url:
        line_item["price_data"]["product_data"]["images"] = [bid.image_url]

    # Default URLs
    app_base = os.getenv("APP_BASE_URL", "http://localhost:3003")
    success_url = body.success_url or f"{app_base}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = body.cancel_url or f"{app_base}/?checkout=cancel"

    # Check for Stripe Connect: look up merchant via bid's seller
    connected_account_id = None
    platform_fee_cents = 0
    commission_rate = float(os.getenv("DEFAULT_PLATFORM_FEE_RATE", "0.05"))
    if bid.seller_id:
        merchant_result = await session.exec(
            select(Merchant).where(Merchant.seller_id == bid.seller_id)
        )
        merchant = merchant_result.first()
        if merchant and merchant.stripe_account_id and merchant.stripe_onboarding_complete:
            connected_account_id = merchant.stripe_account_id
            commission_rate = merchant.default_commission_rate
            platform_fee_cents = int(round(unit_amount * commission_rate))

    session_params = {
        "mode": "payment",
        "line_items": [line_item],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "bid_id": str(bid.id),
            "row_id": str(row.id),
            "user_id": str(auth_session.user_id),
            "commission_rate": str(commission_rate),
        },
    }

    # Add Stripe Connect params if merchant has connected account
    if connected_account_id:
        session_params["payment_intent_data"] = {
            "application_fee_amount": platform_fee_cents,
        }
        session_params["stripe_account"] = connected_account_id
        session_params["metadata"]["connected_account"] = connected_account_id

    try:
        checkout_session = stripe.checkout.Session.create(**session_params)
    except Exception as e:
        logger.error(f"[CHECKOUT] Stripe session creation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to create checkout session")

    await audit_log(
        session=session,
        action="checkout.session_created",
        user_id=auth_session.user_id,
        resource_type="checkout",
        resource_id=checkout_session.id,
        details={
            "bid_id": bid.id,
            "row_id": row.id,
            "amount": bid.price,
            "currency": currency,
        },
    )

    return CheckoutCreateResponse(
        checkout_url=checkout_session.url,
        session_id=checkout_session.id,
    )


# ── Simple checkout alias (frontend calls POST /api/checkout) ───────────

@router.post("/api/checkout", response_model=CheckoutCreateResponse)
async def create_checkout_alias(
    body: CheckoutCreateRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Alias for /api/checkout/create-session to match frontend expectations."""
    return await create_checkout_session(body, authorization, session)


# ── Multi-Vendor Batch Checkout (PRD 05) ────────────────────────────────


class BatchCheckoutRequest(BaseModel):
    bid_ids: list[int]
    row_id: int
    success_url: str = ""
    cancel_url: str = ""


class BatchCheckoutResponse(BaseModel):
    sessions: list[dict]
    total_amount: float
    currency: str


@router.post("/api/checkout/batch", response_model=BatchCheckoutResponse)
async def batch_checkout(
    body: BatchCheckoutRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Create multiple Stripe Checkout Sessions for a batch of bids (PRD 05).
    Each bid gets its own session so different merchants can receive separate payouts.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not body.bid_ids:
        raise HTTPException(status_code=400, detail="No bids specified")

    if len(body.bid_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 bids per batch")

    # Verify row belongs to user
    row_result = await session.exec(
        select(Row).where(Row.id == body.row_id, Row.user_id == auth_session.user_id)
    )
    row = row_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found or access denied")

    sessions_created = []
    total = 0.0
    currency = "USD"

    for bid_id in body.bid_ids:
        bid = await session.get(Bid, bid_id)
        if not bid or bid.row_id != body.row_id:
            continue
        if bid.price is None or bid.price <= 0:
            continue

        # Create individual checkout for this bid
        single_req = CheckoutCreateRequest(
            bid_id=bid_id,
            row_id=body.row_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        try:
            result = await create_checkout_session(single_req, authorization, session)
            sessions_created.append({
                "bid_id": bid_id,
                "checkout_url": result.checkout_url,
                "session_id": result.session_id,
                "amount": bid.price,
                "title": bid.item_title,
            })
            total += bid.price
            currency = (bid.currency or "USD").upper()
        except HTTPException as e:
            logger.warning(f"[BATCH CHECKOUT] Skipped bid {bid_id}: {e.detail}")
            continue

    if not sessions_created:
        raise HTTPException(status_code=400, detail="No valid bids for checkout")

    return BatchCheckoutResponse(
        sessions=sessions_created,
        total_amount=round(total, 2),
        currency=currency,
    )


# ── Stripe Webhook ──────────────────────────────────────────────────────


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    stripe = _get_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"[STRIPE WEBHOOK] Error: {e}")
            raise HTTPException(status_code=400, detail="Webhook error")
    else:
        # Dev mode — parse without verification
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type") if isinstance(event, dict) else event.type

    logger.info(f"[STRIPE WEBHOOK] Received event: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(event)

    return {"status": "received"}


async def _handle_checkout_completed(event):
    """Process a completed checkout session."""
    data = event.get("data", {}) if isinstance(event, dict) else event.data
    session_obj = data.get("object", {}) if isinstance(data, dict) else data.object

    if isinstance(session_obj, dict):
        metadata = session_obj.get("metadata", {})
        stripe_session_id = session_obj.get("id")
        payment_intent_id = session_obj.get("payment_intent")
        amount_total = session_obj.get("amount_total", 0)
        currency = session_obj.get("currency", "usd")
    else:
        metadata = session_obj.metadata or {}
        stripe_session_id = session_obj.id
        payment_intent_id = session_obj.payment_intent
        amount_total = session_obj.amount_total or 0
        currency = session_obj.currency or "usd"

    bid_id = metadata.get("bid_id")
    row_id = metadata.get("row_id")
    user_id = metadata.get("user_id")

    if not bid_id or not row_id:
        logger.warning("[STRIPE WEBHOOK] Missing metadata in checkout session")
        return

    try:
        bid_id = int(bid_id)
        row_id = int(row_id)
        user_id = int(user_id) if user_id else None
    except (ValueError, TypeError):
        logger.warning("[STRIPE WEBHOOK] Invalid metadata values")
        return

    async for db_session in get_session():
        try:
            # Calculate platform fee from metadata
            fee_rate = float(metadata.get("commission_rate", "0.0"))
            connected = metadata.get("connected_account")
            amount_dollars = amount_total / 100.0
            fee_amount = round(amount_dollars * fee_rate, 2) if fee_rate > 0 else None

            purchase = PurchaseEvent(
                user_id=user_id,
                bid_id=bid_id,
                row_id=row_id,
                amount=amount_dollars,
                currency=currency.upper(),
                payment_method="stripe_checkout",
                stripe_session_id=stripe_session_id,
                stripe_payment_intent_id=payment_intent_id,
                status="completed",
                platform_fee_amount=fee_amount,
                commission_rate=fee_rate if fee_rate > 0 else None,
                revenue_type="stripe_connect" if connected else "stripe_checkout",
            )
            db_session.add(purchase)

            # Update row status
            row = await db_session.get(Row, row_id)
            if row:
                row.status = "purchased"
                db_session.add(row)

            # Mark bid as selected and update closing status
            bid = await db_session.get(Bid, bid_id)
            if bid:
                bid.is_selected = True
                bid.closing_status = "paid"
                db_session.add(bid)

            await db_session.commit()
            logger.info(
                f"[STRIPE WEBHOOK] Purchase recorded: bid={bid_id}, row={row_id}, amount={amount_total/100.0}"
            )
        except Exception as e:
            logger.error(f"[STRIPE WEBHOOK] Failed to record purchase: {e}")
            await db_session.rollback()
