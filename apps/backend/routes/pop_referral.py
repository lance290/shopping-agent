"""Pop referral system routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.auth import User
from models.pop import WalletTransaction, Referral, _gen_ref_code
from routes.pop_helpers import POP_DOMAIN, _get_pop_user

logger = logging.getLogger(__name__)
referral_router = APIRouter()


@referral_router.get("/referral")
async def get_pop_referral(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Return the authenticated user's referral code and shareable link.
    Auto-generates a ref_code on first call if one doesn't exist yet.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not user.ref_code:
        user.ref_code = _gen_ref_code()
        session.add(user)
        await session.commit()

    referral_link = f"{POP_DOMAIN}/?ref={user.ref_code}"

    ref_stmt = select(Referral).where(Referral.referrer_user_id == user.id)
    ref_result = await session.execute(ref_stmt)
    referrals = ref_result.scalars().all()

    return {
        "ref_code": user.ref_code,
        "referral_link": referral_link,
        "total_referrals": len(referrals),
        "activated_referrals": sum(1 for r in referrals if r.status == "activated"),
    }


@referral_router.post("/referral/signup")
async def record_referral_signup(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Record that a newly-signed-up user came through a referral link.
    Called during onboarding when ?ref=CODE is present.
    Body: { "ref_code": "ABCD1234" }
    """
    new_user = await _get_pop_user(request, session)
    if not new_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    ref_code = (body.get("ref_code") or "").strip().upper()
    if not ref_code:
        raise HTTPException(status_code=400, detail="ref_code required")

    # Find referrer
    referrer_stmt = select(User).where(User.ref_code == ref_code)
    referrer_result = await session.execute(referrer_stmt)
    referrer = referrer_result.scalar_one_or_none()

    if not referrer or referrer.id == new_user.id:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    # Idempotent — ignore duplicate signup attributions
    existing_stmt = select(Referral).where(Referral.referred_user_id == new_user.id)
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        return {"status": "already_attributed"}

    referral = Referral(
        referrer_user_id=referrer.id,
        referred_user_id=new_user.id,
        ref_code=ref_code,
        status="activated",
        activated_at=datetime.utcnow(),
    )
    session.add(referral)

    # Referral bonus for referrer: $1.00
    referrer.wallet_balance_cents = (referrer.wallet_balance_cents or 0) + 100
    session.add(referrer)
    txn = WalletTransaction(
        user_id=referrer.id,
        amount_cents=100,
        description=f"Referral bonus — friend joined via your link",
        source="referral_bonus",
    )
    session.add(txn)
    await session.commit()

    return {"status": "attributed", "referrer_id": referrer.id}
