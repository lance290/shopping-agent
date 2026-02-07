"""Notification trigger service (PRD 04, 06, 12).

Centralizes notification creation logic so routes don't need to
import and call create_notification directly. Each trigger function
handles the business logic for when/what to notify.
"""

import json
import logging
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import or_

from models import Merchant, Notification, Row

logger = logging.getLogger(__name__)


async def notify_matching_merchants(session: AsyncSession, row: Row) -> int:
    """
    When a new row is created, notify merchants whose categories match.
    Returns count of notifications sent.

    PRD 04: Seller RFP matching notifications.
    """
    if not row.id:
        return 0

    # Determine what to match on
    match_terms: List[str] = []
    if row.service_category:
        match_terms.append(row.service_category.lower())
    if row.title:
        # Extract meaningful words from title (skip short words)
        match_terms.extend(
            w.lower() for w in row.title.split() if len(w) > 3
        )
    if row.search_intent:
        try:
            intent = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(intent, dict):
                cat = intent.get("product_category", "")
                if cat:
                    match_terms.append(cat.lower())
        except (json.JSONDecodeError, TypeError):
            pass

    if not match_terms:
        return 0

    # Find merchants with matching categories
    result = await session.exec(
        select(Merchant).where(
            Merchant.status.in_(["verified", "pending"]),
            Merchant.user_id.isnot(None),
        )
    )
    merchants = result.all()

    sent = 0
    for merchant in merchants:
        if not merchant.categories or not merchant.user_id:
            continue

        try:
            cats = json.loads(merchant.categories) if isinstance(merchant.categories, str) else merchant.categories
            if not isinstance(cats, list):
                cats = [str(cats)]
            merchant_cats = [str(c).lower() for c in cats]
        except (json.JSONDecodeError, TypeError):
            merchant_cats = [merchant.categories.lower()]

        # Check if any merchant category matches any row term
        matched = any(
            term in cat or cat in term
            for term in match_terms
            for cat in merchant_cats
        )

        if not matched:
            continue

        # Don't notify the row owner
        if merchant.user_id == row.user_id:
            continue

        notif = Notification(
            user_id=merchant.user_id,
            type="rfp_match",
            title=f"New buyer need: {row.title}",
            body=f"A buyer is looking for \"{row.title}\". Submit a quote to compete!",
            action_url=f"/seller/inbox",
            resource_type="row",
            resource_id=row.id,
        )
        session.add(notif)
        sent += 1

    if sent > 0:
        await session.flush()
        logger.info(f"[Notify] Sent {sent} RFP match notifications for row {row.id}")

    return sent


async def notify_bid_selected(
    session: AsyncSession,
    row: Row,
    bid_id: int,
    seller_user_id: Optional[int],
) -> None:
    """Notify seller when their bid is selected by the buyer (PRD 04)."""
    if not seller_user_id:
        return

    notif = Notification(
        user_id=seller_user_id,
        type="bid_selected",
        title=f"Your bid was selected!",
        body=f"A buyer selected your offer for \"{row.title}\".",
        action_url=f"/seller/quotes",
        resource_type="bid",
        resource_id=bid_id,
    )
    session.add(notif)
    await session.flush()


async def notify_deal_closed(
    session: AsyncSession,
    row: Row,
    buyer_user_id: int,
    seller_user_id: Optional[int],
) -> None:
    """Notify both parties when a deal is closed (PRD 04/05)."""
    # Notify buyer
    buyer_notif = Notification(
        user_id=buyer_user_id,
        type="deal_closed",
        title=f"Deal completed for \"{row.title}\"",
        body="Your purchase has been confirmed.",
        action_url=f"/projects?row={row.id}",
        resource_type="row",
        resource_id=row.id,
    )
    session.add(buyer_notif)

    # Notify seller
    if seller_user_id:
        seller_notif = Notification(
            user_id=seller_user_id,
            type="deal_closed",
            title=f"Deal completed for \"{row.title}\"",
            body="The buyer has confirmed the purchase.",
            action_url=f"/seller/quotes",
            resource_type="row",
            resource_id=row.id,
        )
        session.add(seller_notif)

    await session.flush()
