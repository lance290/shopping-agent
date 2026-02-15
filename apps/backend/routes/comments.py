"""Comments routes - add/list comments on offers."""
import re
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


def sanitize_html(text: str) -> str:
    """Strip HTML tags from text to prevent XSS."""
    return re.sub(r'<[^>]+>', '', text)

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Comment, Row
from dependencies import get_current_session

router = APIRouter(tags=["comments"])


class CommentCreate(BaseModel):
    row_id: int
    body: str
    bid_id: Optional[int] = None
    offer_url: Optional[str] = None
    visibility: Optional[str] = "private"


class CommentRead(BaseModel):
    id: int
    row_id: int
    user_id: int
    body: str
    bid_id: Optional[int] = None
    offer_url: Optional[str] = None
    visibility: str
    created_at: datetime


@router.post("/comments", response_model=CommentRead)
async def create_comment(
    comment_in: CommentCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not comment_in.body or not comment_in.body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required")

    row = await session.get(Row, comment_in.row_id)
    if not row or row.user_id != auth_session.user_id:
        raise HTTPException(status_code=404, detail="Row not found")

    if not comment_in.bid_id and not comment_in.offer_url:
        raise HTTPException(status_code=400, detail="Must provide bid_id or offer_url")

    db_comment = Comment(
        user_id=auth_session.user_id,
        row_id=comment_in.row_id,
        bid_id=comment_in.bid_id,
        offer_url=comment_in.offer_url,
        body=sanitize_html(comment_in.body.strip()),
        visibility=comment_in.visibility or "private",
    )
    session.add(db_comment)
    await session.commit()
    await session.refresh(db_comment)
    return db_comment


@router.get("/comments", response_model=List[CommentRead])
async def list_comments(
    row_id: Optional[int] = None,
    bid_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    query = select(Comment).where(Comment.user_id == auth_session.user_id, Comment.status != "archived")
    if row_id:
        query = query.where(Comment.row_id == row_id)
    if bid_id:
        query = query.where(Comment.bid_id == bid_id)

    query = query.order_by(Comment.created_at.desc())
    result = await session.exec(query)
    return result.all()


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Delete a comment. Users can only delete their own comments."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    comment = await session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    comment.status = "archived"
    session.add(comment)
    await session.commit()
    return {"status": "archived"}
