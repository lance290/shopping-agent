"""Notification routes — fetch, mark read, create notifications."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy import func, update

from database import get_session
from dependencies import get_current_session
from models import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    read: bool
    created_at: datetime


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """List notifications for the authenticated user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    query = select(Notification).where(
        Notification.user_id == auth_session.user_id
    )

    if unread_only:
        query = query.where(Notification.read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit)

    result = await session.exec(query)
    return result.all()


@router.get("/count")
async def unread_count(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get count of unread notifications."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(func.count(Notification.id)).where(
            Notification.user_id == auth_session.user_id,
            Notification.read == False,
        )
    )
    count = result.one()
    return {"unread": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Mark a notification as read."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    notif = await session.get(Notification, notification_id)
    if not notif or notif.user_id != auth_session.user_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read = True
    notif.read_at = datetime.utcnow()
    session.add(notif)
    await session.commit()

    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Mark all notifications as read for the authenticated user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    await session.execute(
        update(Notification)
        .where(
            Notification.user_id == auth_session.user_id,
            Notification.read == False,
        )
        .values(read=True, read_at=datetime.utcnow())
    )
    await session.commit()

    return {"status": "ok"}


async def create_notification(
    session: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    body: Optional[str] = None,
    action_url: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
) -> Notification:
    """Helper to create a notification (used by other routes)."""
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        action_url=action_url,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(notif)
    await session.flush()
    return notif
