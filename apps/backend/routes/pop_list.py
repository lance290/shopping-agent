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
from services.llm_pop import parse_bulk_grocery_text
from routes.chat_helpers import _create_row

logger = logging.getLogger(__name__)
list_router = APIRouter()

from routes.pop_offers import _classify_swaps_llm  # noqa: F401 — re-exported for backward compat


def _extract_taxonomy(row: Row) -> dict:
    """Extract taxonomy fields (department, brand, size, quantity) from choice_answers."""
    answers = row.choice_answers if isinstance(row.choice_answers, dict) else {}
    return {
        "department": answers.get("department"),
        "brand": answers.get("brand"),
        "size": answers.get("size"),
        "quantity": answers.get("quantity"),
    }


def _item_response(row: Row) -> dict:
    """Build a single-item response dict with taxonomy + attribution."""
    taxonomy = _extract_taxonomy(row)
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "origin_channel": row.origin_channel,
        "origin_user_id": row.origin_user_id,
        **taxonomy,
    }


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

        taxonomy = _extract_taxonomy(row)
        items.append({
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "origin_channel": row.origin_channel,
            "origin_user_id": row.origin_user_id,
            **taxonomy,
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

    project_id = request.query_params.get("project_id")
    if project_id:
        proj_stmt = (
            select(Project)
            .where(Project.id == int(project_id))
            .where(Project.user_id == user.id)
            .where(Project.status == "active")
        )
    else:
        proj_stmt = (
            select(Project)
            .where(Project.user_id == user.id)
            .where(Project.status == "active")
            .order_by(Project.updated_at.desc())
            .limit(1)
        )
    proj_result = await session.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()

    if not project:
        return {"project_id": None, "title": "My Shopping List", "items": []}

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


@list_router.get("/lists")
async def get_pop_lists(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    proj_stmt = (
        select(Project)
        .where(Project.user_id == user.id)
        .where(Project.status == "active")
        .order_by(Project.updated_at.desc())
    )
    result = await session.execute(proj_stmt)
    projects = result.scalars().all()

    return [{"id": p.id, "title": p.title, "created_at": p.created_at.isoformat() if p.created_at else None} for p in projects]


@list_router.post("/list/{project_id}/duplicate")
async def duplicate_pop_list(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found")

    new_project = Project(
        title=f"{project.title} (Copy)",
        user_id=user.id
    )
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    rows_stmt = select(Row).where(Row.project_id == project_id, Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    for row in rows:
        new_row = Row(
            user_id=user.id,
            project_id=new_project.id,
            title=row.title,
            status=row.status,
            is_service=row.is_service,
            service_category=row.service_category,
            choice_answers=row.choice_answers,
            provider_query=row.provider_query,
            desire_tier=row.desire_tier,
            budget_max=row.budget_max,
            currency=row.currency
        )
        session.add(new_row)

    await session.commit()
    return {"project_id": new_project.id, "title": new_project.title}


@list_router.post("/lists")
async def create_pop_list(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    title = body.get("title", "New List").strip() or "New List"
    project = Project(title=title, user_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return {"project_id": project.id, "title": project.title}


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


GROCERY_DEPARTMENTS = [
    "Produce", "Meat", "Dairy", "Pantry", "Frozen",
    "Bakery", "Household", "Personal Care", "Pet", "Other",
]


class PatchItemRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    quantity: Optional[str] = None


@list_router.patch("/item/{row_id}")
async def patch_pop_item(
    row_id: int,
    body: PatchItemRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Update a list item's title and/or taxonomy fields (department, brand, size, quantity)."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = await session.get(Row, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")

    if body.title is not None:
        row.title = body.title.strip()

    answers = dict(row.choice_answers) if isinstance(row.choice_answers, dict) else {}
    changed = False
    for key in ("department", "brand", "size", "quantity"):
        val = getattr(body, key, None)
        if val is not None:
            val_clean = val.strip()
            if not val_clean and key in answers:
                del answers[key]
                changed = True
            elif val_clean and answers.get(key) != val_clean:
                answers[key] = val_clean
                changed = True
    if changed:
        row.choice_answers = answers

    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return _item_response(row)


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


# ---------------------------------------------------------------------------
# Household Member Management (PRD-03)
# ---------------------------------------------------------------------------

@list_router.get("/projects/{project_id}/members")
async def get_project_members(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """List all members of a household/project."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Must be owner or member to view members
    member_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
    )
    member_result = await session.execute(member_stmt)
    if not member_result.scalar_one_or_none() and project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not a member of this list")

    from models.auth import User as AuthUser
    stmt = (
        select(ProjectMember, AuthUser)
        .join(AuthUser, ProjectMember.user_id == AuthUser.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at.asc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    members = []
    for pm, u in rows:
        members.append({
            "user_id": u.id,
            "name": u.name or u.email,
            "email": u.email,
            "role": pm.role,
            "channel": pm.channel,
            "joined_at": pm.joined_at.isoformat() if pm.joined_at else None,
            "is_owner": project.user_id == u.id,
        })

    return {"project_id": project_id, "members": members}


@list_router.delete("/projects/{project_id}/members/{member_user_id}")
async def remove_project_member(
    project_id: int,
    member_user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Remove a member from the household. Only the project owner can do this."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the list owner can remove members")

    if member_user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from your own list")

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_user_id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await session.delete(member)
    await session.commit()
    return {"removed": True, "user_id": member_user_id}


class BulkParseRequest(BaseModel):
    text: str


@list_router.post("/projects/{project_id}/bulk_parse")
async def bulk_parse_items(
    project_id: int,
    body: BulkParseRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Parse a wall of text into multiple grocery list items."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _ensure_project_member(session, project.id, user.id, channel="web")

    from routes.chat_helpers import _create_row

    items = await parse_bulk_grocery_text(body.text)
    if not items:
        return {"parsed_items": 0, "rows": []}

    created_rows = []
    for item in items:
        name = item.get("name")
        if not name:
            continue
        
        constraints = {}
        if item.get("qty"):
            constraints["quantity"] = str(item["qty"])
        if item.get("department"):
            constraints["department"] = str(item["department"])

        row = await _create_row(
            session=session,
            user_id=user.id,
            title=name,
            project_id=project.id,
            is_service=False,
            service_category=None,
            constraints=constraints,
            origin_channel="web"
        )
        created_rows.append(_item_response(row))

    return {"parsed_items": len(created_rows), "rows": created_rows}


@list_router.post("/projects/{project_id}/clear_completed")
async def clear_completed_items(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Sweep all 'closed' (completed) items from the active view."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _ensure_project_member(session, project.id, user.id, channel="web")

    from sqlalchemy import update
    stmt = (
        update(Row)
        .where(Row.project_id == project_id)
        .where(Row.status == "closed")
        .values(status="archived", updated_at=datetime.utcnow())
    )
    result = await session.execute(stmt)
    await session.commit()
    
    return {"cleared": result.rowcount}


# Offer claim/unclaim endpoints moved to routes/pop_offers.py
