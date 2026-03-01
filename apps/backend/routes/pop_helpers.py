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
from models.bids import Bid
from services.coupon_provider import get_coupon_provider
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
        raw = row.chat_history
        if isinstance(raw, list):
            return raw
        history = json.loads(raw)
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
    history = list(_load_chat_history(row))  # copy to ensure SQLAlchemy detects mutation
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    if len(history) > 50:
        history = history[-50:]
    row.chat_history = history
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


async def _build_item_with_deals(session: AsyncSession, row: Row) -> dict:
    """
    Build a list-item dict with deals (bids) attached.
    Used by both the chat response and the list endpoints.
    """
    bids_stmt = (
        select(Bid)
        .where(Bid.row_id == row.id)
        .order_by(Bid.combined_score.desc().nullslast())
        .limit(5)
    )
    bids_result = await session.execute(bids_stmt)
    bids = bids_result.scalars().all()

    deals = []
    swaps = []
    lowest_price = None
    priced_bids = [b for b in bids if b.price is not None]

    for b in priced_bids:
        deal = {
            "id": b.id,
            "title": b.item_title,
            "price": b.price,
            "source": b.source,
            "url": b.canonical_url,
            "image_url": b.image_url,
            "is_selected": b.is_selected or False,
        }
        deals.append(deal)
        if lowest_price is None or b.price < lowest_price:
            lowest_price = b.price
        if b.is_swap:
            swaps.append({
                "id": b.id,
                "title": b.item_title,
                "price": b.price,
                "source": b.source,
                "url": b.canonical_url,
                "image_url": b.image_url,
                "savings_vs_first": round(deals[0]["price"] - b.price, 2) if deals and b.price < deals[0]["price"] else None,
            })

    provider = get_coupon_provider()
    provider_swaps = await provider.search_swaps(category=row.title, product_name=row.title, session=session)
    for s in provider_swaps:
        base_price = deals[0]["price"] if deals else None
        swap_price = base_price - (s.savings_cents / 100) if base_price else None
        if swap_price is not None and swap_price < 0:
            swap_price = 0.0
        
        swaps.append({
            "id": s.swap_id + 1000000 if s.swap_id else 0,
            "title": f"{s.swap_product_name} ({s.offer_description})" if s.offer_description else s.swap_product_name,
            "price": swap_price,
            "source": f"{s.provider.capitalize()} Offer",
            "url": s.swap_product_url,
            "image_url": s.swap_product_image,
            "savings_vs_first": s.savings_cents / 100,
        })

    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "deals": deals,
        "swaps": swaps[:3],
        "lowest_price": lowest_price,
        "deal_count": len(deals),
    }
