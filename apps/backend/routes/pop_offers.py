"""Pop offer claim/unclaim routes + swap classification helper."""

import json
import re
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.rows import Row
from models.bids import Bid
from services.llm import call_gemini
from routes.pop_helpers import _get_pop_user

logger = logging.getLogger(__name__)
offers_router = APIRouter()


async def _classify_swaps_llm(row_title: str, bids: list) -> set:
    """
    Ask Gemini to classify which bids are swap alternatives for a list item.
    Returns a set of bid IDs classified as swaps.
    Bids not in the returned set are direct matches.
    """
    try:
        lines = "\n".join(
            f'{i + 1}. [id={b.id}] "{b.item_title}"'
            for i, b in enumerate(bids)
        )
        prompt = (
            f'A shopper wants: "{row_title}"\n\n'
            f"The following products were found:\n{lines}\n\n"
            f"For each product, decide: is it a DIRECT match (same product, possibly different brand/size) "
            f"or a SWAP (a meaningfully different product that could substitute)?\n\n"
            f'Return ONLY a JSON array of objects: [{{"id": <bid_id>, "is_swap": true|false}}, ...]\n'
            f"No explanation, no markdown, just the JSON array."
        )
        raw = await call_gemini(prompt, timeout=15.0)
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return set()
        classifications = json.loads(match.group())
        return {c["id"] for c in classifications if c.get("is_swap")}
    except Exception as e:
        logger.warning(f"[Pop] Swap classification failed: {e}")
        return set()


@offers_router.post("/offer/{bid_id}/claim")
async def claim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Claim a swap offer (mark bid as selected for this household).
    Only the row owner can claim. One active claim per row.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    if row.status == "canceled":
        raise HTTPException(status_code=409, detail="Cannot claim offer on a canceled item")

    # Clear any prior selection on this row (one active claim per item)
    prior_stmt = select(Bid).where(Bid.row_id == bid.row_id, Bid.is_selected == True)
    prior_result = await session.execute(prior_stmt)
    for prior in prior_result.scalars().all():
        prior.is_selected = False
        prior.liked_at = None
        session.add(prior)

        # Cancel any associated swap claims
        from models.coupons import PopSwapClaim
        claims_stmt = select(PopSwapClaim).where(PopSwapClaim.row_id == row.id, PopSwapClaim.user_id == user.id)
        claims_result = await session.execute(claims_stmt)
        for claim in claims_result.scalars().all():
            claim.status = "canceled"
            session.add(claim)

    # Note: Bid IDs > 1,000,000 are synthesized PopSwap objects from CouponProvider,
    # not actual database Bids. But for real database Bids that have is_swap=True,
    # we might need a mapping to the underlying PopSwap. For now, we assume the frontend
    # sends the synthesized ID (1,000,000 + swap_id).
    swap_id = None
    if bid_id >= 1000000:
        swap_id = bid_id - 1000000
    
    if swap_id:
        from models.coupons import PopSwapClaim
        claim = PopSwapClaim(
            swap_id=swap_id,
            user_id=user.id,
            row_id=row.id,
            status="claimed",
        )
        session.add(claim)
    else:
        bid.is_selected = True
        bid.liked_at = datetime.utcnow()
        session.add(bid)
        
    await session.commit()
    return {"claimed": True, "bid_id": bid_id, "title": bid.item_title if not swap_id else "Swap Offer", "price": bid.price if not swap_id else None}


@offers_router.delete("/offer/{bid_id}/claim")
async def unclaim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Cancel (unclaim) a previously claimed swap offer."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    bid.is_selected = False
    bid.liked_at = None
    session.add(bid)

    swap_id = None
    if bid_id >= 1000000:
        swap_id = bid_id - 1000000
        
    if swap_id:
        from models.coupons import PopSwapClaim
        claims_stmt = select(PopSwapClaim).where(PopSwapClaim.row_id == row.id, PopSwapClaim.user_id == user.id, PopSwapClaim.swap_id == swap_id)
        claims_result = await session.execute(claims_stmt)
        for claim in claims_result.scalars().all():
            claim.status = "canceled"
            session.add(claim)

    await session.commit()
    return {"claimed": False, "bid_id": bid_id}
