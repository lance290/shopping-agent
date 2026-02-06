"""Bids routes - endpoints for individual bid operations."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Bid, BidWithProvenance, Like, Comment
from dependencies import get_current_session

router = APIRouter(tags=["bids"])


class CommentData(BaseModel):
    id: int
    user_id: int
    body: str
    created_at: datetime


class BidSocialData(BaseModel):
    bid_id: int
    like_count: int
    is_liked: bool
    comment_count: int
    comments: List[CommentData]


@router.get("/bids/{bid_id}")
async def get_bid(
    bid_id: int,
    include_provenance: bool = Query(False),
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a bid by ID, optionally with provenance data.

    Args:
        bid_id: The bid ID to fetch
        include_provenance: If True, return BidWithProvenance with parsed provenance data
        authorization: Bearer token for authentication
        session: Database session

    Returns:
        Bid or BidWithProvenance model

    Raises:
        401: If not authenticated
        404: If bid not found
        500: If provenance data is malformed (with graceful fallback)
    """


    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch the bid
    result = await session.exec(select(Bid).where(Bid.id == bid_id))
    bid = result.first()

    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    # Return enhanced bid with provenance if requested
    if include_provenance:
        try:
            # Convert to BidWithProvenance for computed fields
            bid_with_prov = BidWithProvenance.model_validate(bid)
            return bid_with_prov
        except Exception as e:
            # Log the error but return basic bid data as fallback
            print(f"Error parsing provenance for bid {bid_id}: {e}")
            # Return the bid without provenance computed fields
            return bid

    return bid


@router.get("/bids/{bid_id}/social", response_model=BidSocialData)
async def get_bid_social(
    bid_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Get aggregated social data for a bid (likes, comments).

    Args:
        bid_id: The bid ID
        authorization: Bearer token for authentication
        session: Database session

    Returns:
        BidSocialData with like count, user's like status, and comments

    Raises:
        401: If not authenticated
        404: If bid not found
    """


    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify bid exists
    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    # Get like count
    like_count_query = select(func.count(Like.id)).where(Like.bid_id == bid_id)
    like_count_result = await session.exec(like_count_query)
    like_count = like_count_result.one()

    # Check if current user liked this bid
    user_like_query = select(Like).where(
        Like.bid_id == bid_id,
        Like.user_id == auth_session.user_id
    )
    user_like_result = await session.exec(user_like_query)
    is_liked = user_like_result.first() is not None

    # Get comments
    comments_query = (
        select(Comment)
        .where(Comment.bid_id == bid_id)
        .order_by(Comment.created_at.desc())
    )
    comments_result = await session.exec(comments_query)
    comments = comments_result.all()

    comment_data = [
        CommentData(
            id=c.id,
            user_id=c.user_id,
            body=c.body,
            created_at=c.created_at
        )
        for c in comments
    ]

    return BidSocialData(
        bid_id=bid_id,
        like_count=like_count,
        is_liked=is_liked,
        comment_count=len(comment_data),
        comments=comment_data
    )
