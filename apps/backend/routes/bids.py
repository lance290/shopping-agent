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


@router.get("/bids/social/batch")
async def get_bids_social_batch(
    bid_ids: str,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Batch fetch social data for multiple bids in one request.

    Query params:
        bid_ids: Comma-separated list of bid IDs (e.g., "1,2,3,4,5")

    Returns:
        Dict mapping bid_id -> BidSocialData
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        ids = [int(x.strip()) for x in bid_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bid_ids format")

    if not ids:
        return {}

    if len(ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 bid IDs per request")

    # Batch fetch like counts
    like_counts_query = (
        select(Like.bid_id, func.count(Like.id).label("cnt"))
        .where(Like.bid_id.in_(ids))
        .group_by(Like.bid_id)
    )
    like_counts_result = await session.exec(like_counts_query)
    like_counts = {bid_id: cnt for bid_id, cnt in like_counts_result}

    # Batch fetch user's likes
    user_likes_query = select(Like.bid_id).where(
        Like.bid_id.in_(ids),
        Like.user_id == auth_session.user_id,
    )
    user_likes_result = await session.exec(user_likes_query)
    user_liked_ids = set(user_likes_result.all())

    # Batch fetch comments
    comments_query = (
        select(Comment)
        .where(Comment.bid_id.in_(ids))
        .order_by(Comment.created_at.desc())
    )
    comments_result = await session.exec(comments_query)
    all_comments = comments_result.all()

    # Group comments by bid_id
    comments_by_bid: Dict[int, List[CommentData]] = {}
    for c in all_comments:
        if c.bid_id not in comments_by_bid:
            comments_by_bid[c.bid_id] = []
        comments_by_bid[c.bid_id].append(
            CommentData(
                id=c.id,
                user_id=c.user_id,
                body=c.body,
                created_at=c.created_at,
            )
        )

    # Build response
    result = {}
    for bid_id in ids:
        comments = comments_by_bid.get(bid_id, [])
        result[str(bid_id)] = BidSocialData(
            bid_id=bid_id,
            like_count=like_counts.get(bid_id, 0),
            is_liked=bid_id in user_liked_ids,
            comment_count=len(comments),
            comments=comments,
        )

    return result


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
