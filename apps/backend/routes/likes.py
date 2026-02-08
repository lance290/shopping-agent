"""Likes routes - like/unlike offers via Bid.is_liked."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, Bid
from dependencies import get_current_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["likes"])


class LikeCreate(BaseModel):
    row_id: Optional[int] = None
    bid_id: Optional[int] = None
    offer_url: Optional[str] = None


class LikeResponse(BaseModel):
    bid_id: int
    row_id: int
    is_liked: bool
    liked_at: Optional[datetime] = None


async def _resolve_bid(
    session: AsyncSession, bid_id: Optional[int], row_id: Optional[int], user_id: int
) -> Bid:
    """Resolve and authorize a bid from bid_id or row_id."""
    if bid_id:
        bid = await session.get(Bid, bid_id)
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide bid_id")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Row not found")

    return bid


@router.get("/likes")
async def list_likes(
    row_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Return liked bids for the user, optionally filtered by row_id."""
    from sqlmodel import select

    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        query = select(Bid).where(Bid.is_liked == True)
        if row_id:
            # Verify row ownership
            row = await session.get(Row, row_id)
            if not row or row.user_id != auth_session.user_id:
                raise HTTPException(status_code=404, detail="Row not found")
            query = query.where(Bid.row_id == row_id)
        else:
            # Filter to user's rows
            query = query.join(Row).where(Row.user_id == auth_session.user_id)

        result = await session.exec(query)
        bids = result.all()
        return [
            LikeResponse(
                bid_id=b.id, row_id=b.row_id,
                is_liked=True, liked_at=b.liked_at
            )
            for b in bids
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch likes: {e}")


@router.post("/likes/{bid_id}/toggle")
async def toggle_like(
    bid_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Toggle like on a bid. Returns liked status."""
    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        bid = await _resolve_bid(session, bid_id, None, auth_session.user_id)

        if bid.is_liked:
            bid.is_liked = False
            bid.liked_at = None
        else:
            bid.is_liked = True
            bid.liked_at = datetime.utcnow()

        session.add(bid)
        await session.commit()

        return {
            "is_liked": bid.is_liked,
            "like_count": 1 if bid.is_liked else 0,
            "bid_id": bid_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle like for bid_id={bid_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to toggle like: {e}")
