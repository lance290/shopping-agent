"""User signal collection routes (PRD 11 — Personalized Ranking).

Collects explicit user feedback signals (thumbs up/down, skip) on bids
to enable future ranking personalization.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func

from database import get_session
from dependencies import get_current_session
from models import UserSignal, UserPreference, Bid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


class SignalCreate(BaseModel):
    bid_id: Optional[int] = None
    row_id: Optional[int] = None
    signal_type: str  # "thumbs_up", "thumbs_down", "click", "select", "skip"
    value: float = 1.0


class SignalResponse(BaseModel):
    id: int
    signal_type: str
    bid_id: Optional[int] = None
    row_id: Optional[int] = None
    value: float
    created_at: datetime


@router.post("", response_model=SignalResponse)
async def record_signal(
    body: SignalCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Record a user interaction signal for ranking personalization."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    valid_types = {"thumbs_up", "thumbs_down", "click", "select", "skip"}
    if body.signal_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signal_type. Must be one of: {', '.join(valid_types)}",
        )

    signal = UserSignal(
        user_id=auth_session.user_id,
        bid_id=body.bid_id,
        row_id=body.row_id,
        signal_type=body.signal_type,
        value=body.value,
    )
    session.add(signal)
    await session.commit()
    await session.refresh(signal)

    # Update learned preferences based on signal
    if body.bid_id and body.signal_type in ("thumbs_up", "select"):
        await _learn_from_signal(session, auth_session.user_id, body.bid_id, positive=True)
    elif body.bid_id and body.signal_type == "thumbs_down":
        await _learn_from_signal(session, auth_session.user_id, body.bid_id, positive=False)

    return SignalResponse(
        id=signal.id,
        signal_type=signal.signal_type,
        bid_id=signal.bid_id,
        row_id=signal.row_id,
        value=signal.value,
        created_at=signal.created_at,
    )


@router.get("/preferences")
async def get_preferences(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get learned user preferences."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(UserPreference)
        .where(UserPreference.user_id == auth_session.user_id)
        .order_by(UserPreference.weight.desc())
        .limit(50)
    )
    prefs = result.all()

    return [
        {
            "key": p.preference_key,
            "value": p.preference_value,
            "weight": p.weight,
        }
        for p in prefs
    ]


async def _learn_from_signal(
    session: AsyncSession,
    user_id: int,
    bid_id: int,
    positive: bool,
) -> None:
    """Extract preference signals from a bid the user interacted with."""
    bid = await session.get(Bid, bid_id)
    if not bid:
        return

    import json

    # Extract merchant preference
    if bid.seller_id:
        from models import Seller
        seller = await session.get(Seller, bid.seller_id)
        if seller and seller.domain:
            await _upsert_preference(
                session, user_id, "merchant", seller.domain,
                delta=0.1 if positive else -0.1,
            )

    # Extract source preference
    if bid.source:
        await _upsert_preference(
            session, user_id, "source", bid.source,
            delta=0.05 if positive else -0.05,
        )

    # Extract brand preference from provenance
    if bid.provenance:
        try:
            prov = json.loads(bid.provenance) if isinstance(bid.provenance, str) else bid.provenance
            product_info = prov.get("product_info", {})
            brand = product_info.get("brand")
            if brand:
                await _upsert_preference(
                    session, user_id, "brand", brand,
                    delta=0.15 if positive else -0.15,
                )
        except (json.JSONDecodeError, TypeError):
            pass

    await session.flush()


async def _upsert_preference(
    session: AsyncSession,
    user_id: int,
    key: str,
    value: str,
    delta: float,
) -> None:
    """Create or update a user preference weight."""
    result = await session.exec(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == key,
            UserPreference.preference_value == value,
        )
    )
    pref = result.first()

    if pref:
        pref.weight = max(0.0, min(5.0, pref.weight + delta))
        pref.updated_at = datetime.utcnow()
        session.add(pref)
    else:
        new_pref = UserPreference(
            user_id=user_id,
            preference_key=key,
            preference_value=value,
            weight=max(0.0, min(5.0, 1.0 + delta)),
        )
        session.add(new_pref)
