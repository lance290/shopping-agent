"""Pop list, invite, item CRUD, and offer claim routes."""

import json
import re
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.rows import Row, Project, ProjectInvite
from models.bids import Bid
from services.llm import call_gemini
from routes.pop_helpers import POP_DOMAIN, _get_pop_user, _ensure_project_member, _build_item_with_deals
from models.rows import ProjectMember
from services.coupon_provider import get_coupon_provider

logger = logging.getLogger(__name__)
list_router = APIRouter()


async def _classify_swaps_llm(row_title: str, bids: list) -> set:
    """
    Ask Gemini to classify which bids are swap alternatives for a list item.
    Returns a set of bid IDs classified as swaps.
    Bids not in the returned set are direct matches.
    """
    try:
        lines = "\n".join(
            f'{i + 1}. [id={b.id}] "{b.item_title}"'
            for i, b in enumerate(bids)
        )
        prompt = (
            f'A shopper wants: "{row_title}"\n\n'
            f"The following products were found:\n{lines}\n\n"
            f"For each product, decide: is it a DIRECT match (same product, possibly different brand/size) "
            f"or a SWAP (a meaningfully different product that could substitute)?\n\n"
            f'Return ONLY a JSON array of objects: [{{"id": <bid_id>, "is_swap": true|false}}, ...]\n'
            f"No explanation, no markdown, just the JSON array."
        )
        raw = await call_gemini(prompt, timeout=15.0)
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return set()
        classifications = json.loads(match.group())
        return {item["id"] for item in classifications if item.get("is_swap")}
    except Exception as e:
        logger.warning(f"[Pop] LLM swap classification failed: {e}")
        return set()


@list_router.get("/list/{project_id}")
async def get_pop_list(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch the family shopping list for the Pop list view.
    Requires authentication and membership (owner or member) in the project.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    # Verify the caller is the owner or a member of this project
    membership_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
    )
    membership_result = await session.execute(membership_stmt)
    if not membership_result.scalar_one_or_none() and project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not a member of this list")

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project_id)
        .where(Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
        .order_by(Row.created_at.desc())
        .limit(50)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    provider = get_coupon_provider()
    items = []
    for row in rows:
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

        # LLM swap classification: classify any unclassified bids in one Gemini call
        unclassified = [b for b in priced_bids if b.is_swap is None]
        if unclassified and row.title:
            swap_ids = await _classify_swaps_llm(row.title, unclassified)
            for b in unclassified:
                b.is_swap = b.id in swap_ids
                session.add(b)
            await session.commit()

        for b in priced_bids:
            deal = {
                "id": b.id,
                "title": b.item_title,
                "price": b.price,
                "source": b.source,
                "url": b.canonical_url,
                "image_url": b.image_url,
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

        # Fetch provider swaps (brand coupons/rebates)
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

        items.append({
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "deals": deals,
            "swaps": swaps[:3],
            "lowest_price": lowest_price,
            "deal_count": len(deals),
        })

    return {
        "project_id": project_id,
        "title": project.title,
        "items": items,
    }


@list_router.get("/my-list")
async def get_my_pop_list(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Return the current user's active Family Shopping List project + items.
    Used on page load to restore list state without knowing the project_id upfront.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    proj_stmt = (
        select(Project)
        .where(Project.user_id == user.id)
        .where(Project.title == "Family Shopping List")
        .where(Project.status == "active")
    )
    proj_result = await session.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()

    if not project:
        return {"project_id": None, "title": "Family Shopping List", "items": []}

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project.id)
        .where(Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
        .order_by(Row.created_at.asc())
        .limit(50)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    items = [await _build_item_with_deals(session, r) for r in rows]
    return {"project_id": project.id, "title": project.title, "items": items}


@list_router.post("/list/{project_id}/invite")
async def create_pop_invite(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Create an opaque invite token for sharing a Pop list.
    Returns a shareable invite URL.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    # Only the project owner can create invite links
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the list owner can create invites")

    token = str(uuid.uuid4())
    invite = ProjectInvite(
        id=token,
        project_id=project_id,
        invited_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(invite)
    await session.commit()

    invite_url = f"{POP_DOMAIN}/pop-site/invite/{token}"
    return {"token": token, "invite_url": invite_url, "expires_days": 30}


@list_router.get("/invite/{token}")
async def resolve_pop_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Public endpoint: resolve an invite token to project info (title, item count).
    Does NOT require authentication — used to preview the list before login.
    """
    invite = await session.get(ProjectInvite, token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invite link has expired")

    project = await session.get(Project, invite.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project.id)
        .where(Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
    )
    rows_result = await session.execute(rows_stmt)
    items = rows_result.scalars().all()

    return {
        "project_id": project.id,
        "title": project.title,
        "item_count": len(items),
        "token": token,
    }


class JoinListRequest(BaseModel):
    token: str


@list_router.post("/join-list/{project_id}")
async def join_pop_list(
    project_id: int,
    body: JoinListRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Add the authenticated user as a member of the given shared Pop list.
    Requires a valid, non-expired invite token that maps to this project.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate the invite token
    invite = await session.get(ProjectInvite, body.token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invite token")
    if invite.project_id != project_id:
        raise HTTPException(status_code=403, detail="Invite token does not match this list")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invite link has expired")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    await _ensure_project_member(session, project.id, user.id, channel="web", role="member")
    return {"joined": True, "project_id": project.id, "title": project.title}


class PatchItemRequest(BaseModel):
    title: str


@list_router.patch("/item/{row_id}")
async def patch_pop_item(
    row_id: int,
    body: PatchItemRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Rename a list item."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = await session.get(Row, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")

    row.title = body.title.strip()
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"id": row.id, "title": row.title, "status": row.status}


@list_router.delete("/item/{row_id}")
async def delete_pop_item(
    row_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Remove a list item (soft-delete to avoid FK constraint on bids)."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = await session.get(Row, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")

    row.status = "canceled"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"deleted": True}


@list_router.post("/offer/{bid_id}/claim")
async def claim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Claim a swap offer (mark bid as selected for this household).
    Only the row owner can claim. One active claim per row.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    if row.status == "canceled":
        raise HTTPException(status_code=409, detail="Cannot claim offer on a canceled item")

    # Clear any prior selection on this row (one active claim per item)
    prior_stmt = select(Bid).where(Bid.row_id == bid.row_id, Bid.is_selected == True)
    prior_result = await session.execute(prior_stmt)
    for prior in prior_result.scalars().all():
        prior.is_selected = False
        prior.liked_at = None
        session.add(prior)

        # Cancel any associated swap claims
        from models.coupons import PopSwapClaim
        claims_stmt = select(PopSwapClaim).where(PopSwapClaim.row_id == row.id, PopSwapClaim.user_id == user.id)
        claims_result = await session.execute(claims_stmt)
        for claim in claims_result.scalars().all():
            claim.status = "canceled"
            session.add(claim)

    # Note: Bid IDs > 1,000,000 are synthesized PopSwap objects from CouponProvider,
    # not actual database Bids. But for real database Bids that have is_swap=True,
    # we might need a mapping to the underlying PopSwap. For now, we assume the frontend
    # sends the synthesized ID (1,000,000 + swap_id).
    swap_id = None
    if bid_id >= 1000000:
        swap_id = bid_id - 1000000
    
    if swap_id:
        from models.coupons import PopSwapClaim
        claim = PopSwapClaim(
            swap_id=swap_id,
            user_id=user.id,
            row_id=row.id,
            status="claimed",
        )
        session.add(claim)
    else:
        bid.is_selected = True
        bid.liked_at = datetime.utcnow()
        session.add(bid)
        
    await session.commit()
    return {"claimed": True, "bid_id": bid_id, "title": bid.item_title if not swap_id else "Swap Offer", "price": bid.price if not swap_id else None}


@list_router.delete("/offer/{bid_id}/claim")
async def unclaim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Cancel (unclaim) a previously claimed swap offer."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    bid.is_selected = False
    bid.liked_at = None
    session.add(bid)

    swap_id = None
    if bid_id >= 1000000:
        swap_id = bid_id - 1000000
        
    if swap_id:
        from models.coupons import PopSwapClaim
        claims_stmt = select(PopSwapClaim).where(PopSwapClaim.row_id == row.id, PopSwapClaim.user_id == user.id, PopSwapClaim.swap_id == swap_id)
        claims_result = await session.execute(claims_stmt)
        for claim in claims_result.scalars().all():
            claim.status = "canceled"
            session.add(claim)

    await session.commit()
    return {"claimed": False, "bid_id": bid_id}
