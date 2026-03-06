"""Pop social layer routes: per-item likes and comments (PRD-07)."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select, and_
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.auth import User
from models.rows import Row, ProjectMember
from models.social import RowReaction, RowComment
from routes.pop_helpers import _get_pop_user

logger = logging.getLogger(__name__)
social_router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_pop_user(request: Request, session: AsyncSession) -> User:
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def _require_membership(session: AsyncSession, row_id: int, user_id: int) -> Row:
    """Verify user is a member of the project that owns this row."""
    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if row.project_id:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == row.project_id,
            ProjectMember.user_id == user_id,
        )
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a member of this list")
    return row


# ---------------------------------------------------------------------------
# Reactions (Likes)
# ---------------------------------------------------------------------------

@social_router.post("/item/{row_id}/react")
async def toggle_reaction(
    row_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Toggle a like on a list item. Returns the new state."""
    user = await _require_pop_user(request, session)
    await _require_membership(session, row_id, user.id)

    stmt = select(RowReaction).where(
        RowReaction.row_id == row_id,
        RowReaction.user_id == user.id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        await session.delete(existing)
        await session.commit()
        liked = False
    else:
        reaction = RowReaction(row_id=row_id, user_id=user.id, reaction_type="like")
        session.add(reaction)
        await session.commit()
        liked = True

    # Return updated count
    count_stmt = select(RowReaction).where(RowReaction.row_id == row_id)
    count_result = await session.execute(count_stmt)
    total = len(count_result.scalars().all())

    return {"liked": liked, "like_count": total}


@social_router.get("/item/{row_id}/reactions")
async def get_reactions(
    row_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get reaction summary for an item."""
    user = await _get_pop_user(request, session)

    stmt = select(RowReaction).where(RowReaction.row_id == row_id)
    result = await session.execute(stmt)
    reactions = result.scalars().all()

    user_liked = False
    if user:
        user_liked = any(r.user_id == user.id for r in reactions)

    # Fetch names for each reactor
    reactors = []
    for r in reactions:
        u = await session.get(User, r.user_id)
        reactors.append({
            "user_id": r.user_id,
            "name": u.name or u.email or "Someone",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "like_count": len(reactions),
        "user_liked": user_liked,
        "reactors": reactors,
    }


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class CommentCreateBody(BaseModel):
    text: str


@social_router.post("/item/{row_id}/comments")
async def add_comment(
    row_id: int,
    body: CommentCreateBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Add a comment to a list item."""
    user = await _require_pop_user(request, session)
    await _require_membership(session, row_id, user.id)

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Comment too long (max 500 chars)")

    comment = RowComment(row_id=row_id, user_id=user.id, text=text)
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return {
        "id": comment.id,
        "row_id": comment.row_id,
        "user_id": comment.user_id,
        "user_name": user.name or user.email or "Someone",
        "text": comment.text,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@social_router.get("/item/{row_id}/comments")
async def get_comments(
    row_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get all comments for a list item, newest first."""
    stmt = (
        select(RowComment)
        .where(RowComment.row_id == row_id, RowComment.status == "active")
        .order_by(RowComment.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    comments = result.scalars().all()

    items = []
    for c in comments:
        u = await session.get(User, c.user_id)
        items.append({
            "id": c.id,
            "row_id": c.row_id,
            "user_id": c.user_id,
            "user_name": u.name or u.email or "Someone" if u else "Someone",
            "text": c.text,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"comments": items, "total": len(items)}


@social_router.delete("/item/{row_id}/comments/{comment_id}")
async def delete_comment(
    row_id: int,
    comment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete a comment (only the author can delete)."""
    user = await _require_pop_user(request, session)

    comment = await session.get(RowComment, comment_id)
    if not comment or comment.row_id != row_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your comment")

    comment.status = "deleted"
    session.add(comment)
    await session.commit()

    return {"status": "deleted"}
