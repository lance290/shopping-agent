"""Shared helpers for Pop routes: auth, project membership, chat history."""

import json
import os
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session  # noqa: F401 — re-exported for convenience
from models.rows import Row, Project, ProjectMember
from models.auth import User
from dependencies import get_current_session

logger = logging.getLogger(__name__)

POP_FROM_EMAIL = os.getenv("POP_FROM_EMAIL", "pop@popsavings.com")
POP_DOMAIN = os.getenv("POP_DOMAIN", "https://popsavings.com")
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")


async def _get_pop_user(request: Request, session: AsyncSession) -> Optional[User]:
    """Resolve the current user from a Bearer token, or return None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    auth_session = await get_current_session(auth_header, session)
    if not auth_session:
        return None
    return await session.get(User, auth_session.user_id)


def _load_chat_history(row: Optional[Row]) -> List[dict]:
    """Load conversation history from the active Row's chat_history JSON field."""
    if not row or not row.chat_history:
        return []
    try:
        history = json.loads(row.chat_history)
        if isinstance(history, list):
            return history
    except (json.JSONDecodeError, TypeError):
        pass
    return []


async def _append_chat_history(
    session: AsyncSession,
    row: Row,
    user_message: str,
    assistant_message: str,
) -> None:
    """Append the latest user + assistant exchange to Row.chat_history."""
    history = _load_chat_history(row)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    if len(history) > 50:
        history = history[-50:]
    row.chat_history = json.dumps(history)
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()


async def _ensure_project_member(
    session: AsyncSession,
    project_id: int,
    user_id: int,
    channel: str = "email",
    role: str = "owner",
) -> ProjectMember:
    """Ensure the user is a member of the project; create if not."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()
    if member:
        if member.channel != channel:
            member.channel = channel
            session.add(member)
            await session.commit()
        return member
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        channel=channel,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member
