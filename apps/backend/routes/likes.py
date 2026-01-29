"""Likes routes - like/unlike offers."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy import func
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Like, Row

logger = logging.getLogger(__name__)

router = APIRouter(tags=["likes"])


class LikeCreate(BaseModel):
    row_id: int
    bid_id: Optional[int] = None
    offer_url: Optional[str] = None


class LikeRead(BaseModel):
    id: int
    row_id: int
    bid_id: Optional[int] = None
    offer_url: Optional[str] = None
    created_at: datetime


@router.post("/likes", response_model=LikeRead)
async def create_like(
    like_in: LikeCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session

    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        row = await session.get(Row, like_in.row_id)
        if not row or row.user_id != auth_session.user_id:
            raise HTTPException(status_code=404, detail="Row not found")

        query = select(Like).where(
            Like.user_id == auth_session.user_id,
            Like.row_id == like_in.row_id
        )
        if like_in.bid_id:
            query = query.where(Like.bid_id == like_in.bid_id)
        elif like_in.offer_url:
            query = query.where(Like.offer_url == like_in.offer_url)
        else:
            raise HTTPException(status_code=400, detail="Must provide bid_id or offer_url")

        existing = await session.exec(query)
        if existing.first():
            raise HTTPException(status_code=409, detail="Already liked")

        db_like = Like(
            user_id=auth_session.user_id,
            row_id=like_in.row_id,
            bid_id=like_in.bid_id,
            offer_url=like_in.offer_url
        )
        session.add(db_like)
        await session.commit()
        await session.refresh(db_like)
        return db_like
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create like for row_id={like_in.row_id}, bid_id={like_in.bid_id}, offer_url={like_in.offer_url}: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create like: {str(e)}")


@router.delete("/likes")
async def delete_like(
    row_id: int,
    bid_id: Optional[int] = None,
    offer_url: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session

    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        query = select(Like).where(
            Like.user_id == auth_session.user_id,
            Like.row_id == row_id
        )
        if bid_id:
            query = query.where(Like.bid_id == bid_id)
        elif offer_url:
            query = query.where(Like.offer_url == offer_url)
        else:
            raise HTTPException(status_code=400, detail="Must provide bid_id or offer_url")

        result = await session.exec(query)
        like = result.first()

        if not like:
            raise HTTPException(status_code=404, detail="Like not found")

        await session.delete(like)
        await session.commit()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete like: {str(e)}")


@router.get("/likes", response_model=List[LikeRead])
async def list_likes(
    row_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session

    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        query = select(Like).where(Like.user_id == auth_session.user_id)
        if row_id:
            query = query.where(Like.row_id == row_id)

        result = await session.exec(query)
        return result.all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch likes: {str(e)}")


@router.get("/likes/counts")
async def get_like_counts(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, int]:
    """Get like counts for all offers in a row, grouped by bid_id or offer_url."""
    from routes.auth import get_current_session

    try:
        auth_session = await get_current_session(authorization, session)
        if not auth_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Verify row access
        row = await session.get(Row, row_id)
        if not row or row.user_id != auth_session.user_id:
            raise HTTPException(status_code=404, detail="Row not found")

        # Get counts for bid_id likes
        bid_counts_query = (
            select(Like.bid_id, func.count(Like.id).label('count'))
            .where(Like.row_id == row_id, Like.bid_id.is_not(None))
            .group_by(Like.bid_id)
        )
        bid_results = await session.exec(bid_counts_query)

        # Get counts for offer_url likes
        url_counts_query = (
            select(Like.offer_url, func.count(Like.id).label('count'))
            .where(Like.row_id == row_id, Like.offer_url.is_not(None))
            .group_by(Like.offer_url)
        )
        url_results = await session.exec(url_counts_query)

        # Build response dict
        counts = {}
        for bid_id, count in bid_results:
            counts[f"bid_{bid_id}"] = count
        for url, count in url_results:
            counts[f"url_{url}"] = count

        return counts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get like counts: {str(e)}")
