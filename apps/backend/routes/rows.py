"""Rows routes - CRUD for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Any, Optional, List
from datetime import datetime
import json

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, defer, joinedload

from database import get_session
from models import Row, RowBase, RowCreate, RequestSpec, Bid, Project, User, Vendor
from models.deals import Deal, DealMessage
from dependencies import get_current_session, resolve_user_id, resolve_user_id_and_guest_flag, GUEST_EMAIL
from routes.rows_search import router as rows_search_router
from sourcing.safety import SafetyService
from services.sdui_builder import augment_schema_with_active_deal
from utils.json_utils import safe_json_loads

router = APIRouter(tags=["rows"])
router.include_router(rows_search_router)


def filter_bids_by_price(row: Row) -> List:
    """Filter row.bids using the unified should_include_result filter."""
    from sourcing.filters import should_include_result
    from routes.rows_search import _extract_filters

    if not row.bids:
        return []

    min_price, max_price, _ = _extract_filters(row, None)

    filtered = []
    for bid in row.bids:
        source = (getattr(bid, "source", "") or "").lower()

        if should_include_result(
            price=bid.price,
            source=source,
            desire_tier=getattr(row, "desire_tier", None),
            min_price=min_price,
            max_price=max_price,
            is_service_provider=getattr(bid, "is_service_provider", False),
        ):
            filtered.append(bid)
    
    return filtered


class SellerRead(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None


class BidRead(BaseModel):
    id: int
    price: Optional[float] = None
    currency: str
    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    is_selected: bool = False
    is_liked: bool = False
    liked_at: Optional[datetime] = None
    is_service_provider: bool = False
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    seller: Optional[SellerRead] = None


class ActiveDealRead(BaseModel):
    id: int
    row_id: int
    status: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    bid_id: Optional[int] = None
    vendor_quoted_price: Optional[float] = None
    buyer_total: Optional[float] = None
    currency: str = "USD"
    agreed_terms_summary: Optional[str] = None
    agreement_source: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    terms_agreed_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None
    vendor_stripe_onboarded: Optional[bool] = None


class RowReadWithBids(RowBase):
    id: int
    user_id: int
    project_id: Optional[int] = None
    bids: List[BidRead] = []
    ui_schema: Optional[Any] = None  # SDUI schema (JSONB)
    active_deal: Optional[ActiveDealRead] = None


class RequestSpecUpdate(BaseModel):
    item_name: Optional[str] = None
    constraints: Optional[str] = None
    preferences: Optional[str] = None


class RowUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    budget_max: Optional[float] = None
    request_spec: Optional[RequestSpecUpdate] = None
    choice_factors: Optional[str] = None
    choice_answers: Optional[str] = None
    provider_query_map: Optional[dict] = None
    selected_bid_id: Optional[int] = None
    regenerate_choice_factors: Optional[bool] = None
    chat_history: Optional[str] = None
    reset_bids: Optional[bool] = None
    is_service: Optional[bool] = None
    service_category: Optional[str] = None


def _default_choice_factors_for_row(row: Row) -> list:
    """Return empty factors — LLM generates proper contextual factors via regenerate_choice_factors."""
    return []


_DEAL_STATUS_PRIORITY = {
    "terms_agreed": 0,
    "funded": 1,
    "in_transit": 2,
    "completed": 3,
    "negotiating": 4,
    "disputed": 5,
}


def _infer_agreement_source(content_text: Optional[str]) -> Optional[str]:
    if not content_text:
        return None
    lowered = content_text.lower()
    if "source: auto_detected" in lowered:
        return "auto_detected"
    if "source: manual_reopen" in lowered:
        return "manual_reopen"
    if "source: manual" in lowered:
        return "manual"
    return None


def _choose_active_deal(deals: List[Deal]) -> Optional[Deal]:
    if not deals:
        return None
    return sorted(
        deals,
        key=lambda deal: (
            _DEAL_STATUS_PRIORITY.get(deal.status, 99),
            -(deal.updated_at or deal.created_at).timestamp(),
        ),
    )[0]


async def _load_active_deal_summaries(session: AsyncSession, rows: List[Row]) -> dict[int, dict]:
    row_ids = [row.id for row in rows if row.id is not None]
    if not row_ids:
        return {}

    deal_result = await session.exec(
        select(Deal).where(Deal.row_id.in_(row_ids), Deal.status != "canceled")
    )
    deals = deal_result.all()
    deals_by_row: dict[int, List[Deal]] = {}
    for deal in deals:
        deals_by_row.setdefault(deal.row_id, []).append(deal)

    selected_deals = [chosen for chosen in (_choose_active_deal(group) for group in deals_by_row.values()) if chosen]
    if not selected_deals:
        return {}

    selected_deal_ids = [deal.id for deal in selected_deals if deal.id is not None]
    vendor_ids = [deal.vendor_id for deal in selected_deals if deal.vendor_id is not None]

    vendor_names: dict[int, str] = {}
    vendor_onboarded: dict[int, bool] = {}
    if vendor_ids:
        vendors = (await session.exec(select(Vendor).where(Vendor.id.in_(vendor_ids)))).all()
        vendor_names = {vendor.id: vendor.name for vendor in vendors if vendor.id is not None}
        vendor_onboarded = {vendor.id: bool(vendor.stripe_onboarding_complete) for vendor in vendors if vendor.id is not None}

    source_by_deal: dict[int, Optional[str]] = {}
    if selected_deal_ids:
        message_result = await session.exec(
            select(DealMessage)
            .where(DealMessage.deal_id.in_(selected_deal_ids), DealMessage.sender_type == "system")
            .order_by(DealMessage.created_at.desc())
        )
        for message in message_result.all():
            if message.deal_id not in source_by_deal:
                source_by_deal[message.deal_id] = _infer_agreement_source(message.content_text)

    summaries: dict[int, dict] = {}
    for deal in selected_deals:
        summaries[deal.row_id] = {
            "id": deal.id,
            "row_id": deal.row_id,
            "status": deal.status,
            "vendor_id": deal.vendor_id,
            "vendor_name": vendor_names.get(deal.vendor_id) if deal.vendor_id else None,
            "bid_id": deal.bid_id,
            "vendor_quoted_price": deal.vendor_quoted_price,
            "buyer_total": deal.buyer_total,
            "currency": deal.currency,
            "agreed_terms_summary": deal.agreed_terms_summary,
            "agreement_source": source_by_deal.get(deal.id),
            "stripe_payment_intent_id": deal.stripe_payment_intent_id,
            "terms_agreed_at": deal.terms_agreed_at,
            "funded_at": deal.funded_at,
            "vendor_stripe_onboarded": vendor_onboarded.get(deal.vendor_id, None) if deal.vendor_id else None,
        }
    return summaries


def _serialize_row(row: Row, active_deal: Optional[dict]) -> dict:
    payload = RowReadWithBids.model_validate(row, from_attributes=True).model_dump()
    payload["active_deal"] = active_deal
    payload["ui_schema"] = augment_schema_with_active_deal(payload.get("ui_schema"), active_deal, row)
    return payload


@router.post("/rows", response_model=Row)
async def create_row(
    row: RowCreate,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id = await resolve_user_id(authorization, session)

    if row.project_id is not None:
        project = await session.get(Project, row.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="Project not found")
        if project.user_id != user_id:
            raise HTTPException(status_code=403, detail="Project not owned by user")

    request_spec_data = row.request_spec
    
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency,
        user_id=user_id,
        project_id=row.project_id,
        choice_factors=row.choice_factors,
        choice_answers=row.choice_answers,
        is_service=row.is_service,
        service_category=row.service_category,
        anonymous_session_id=x_anonymous_session_id,
    )
    if db_row.choice_factors is None:
        db_row.choice_factors = _default_choice_factors_for_row(db_row)

    # Safety check
    if row.title:
        check = SafetyService.check_safety(row.title)
        if check["status"] != "safe":
            answers = safe_json_loads(db_row.choice_answers, {})
            answers["safety_status"] = check["status"]
            answers["safety_reason"] = check["reason"]
            db_row.choice_answers = answers

    session.add(db_row)
    await session.commit()
    await session.refresh(db_row)
    
    db_spec = RequestSpec(
        row_id=db_row.id,
        item_name=request_spec_data.item_name,
        constraints=request_spec_data.constraints,
        preferences=request_spec_data.preferences
    )
    session.add(db_spec)
    await session.commit()

    # PRD 04: Notify matching merchants about this new buyer need
    try:
        from services.notify import notify_matching_merchants
        await notify_matching_merchants(session, db_row)
        await session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[ROWS] Merchant notification failed (non-fatal): {e}")
    
    await session.refresh(db_row)
    return db_row


@router.get("/rows", response_model=List[RowReadWithBids])
async def read_rows(
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    
    user_id, is_guest = await resolve_user_id_and_guest_flag(authorization, session)

    # Build where clauses
    where_clauses = [
        Row.user_id == user_id,
        True if include_archived else (Row.status != "archived"),
    ]

    # For guest users, scope to their browser session
    if is_guest and x_anonymous_session_id:
        where_clauses.append(Row.anonymous_session_id == x_anonymous_session_id)
    elif is_guest:
        # No session ID provided — return empty to avoid leaking all guest rows
        return []

    result = await session.exec(
        select(Row)
        .where(*where_clauses)
        .options(
            selectinload(Row.bids).options(
                joinedload(Bid.seller),
                defer(Bid.source_payload),
                defer(Bid.provenance)
            )
        )
        .order_by(Row.updated_at.desc())
    )
    rows = result.all()
    
    # Apply price filters from choice_answers to each row's bids
    for row in rows:
        row.bids = [b for b in row.bids if not b.is_superseded]
        row.bids = filter_bids_by_price(row)

    active_deals = await _load_active_deal_summaries(session, rows)
    return [_serialize_row(row, active_deals.get(row.id)) for row in rows]


@router.get("/rows/{row_id}", response_model=RowReadWithBids)
async def read_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id, is_guest = await resolve_user_id_and_guest_flag(authorization, session)

    result = await session.exec(
        select(Row)
        .where(Row.id == row_id, Row.user_id == user_id)
        .options(
            selectinload(Row.bids).options(
                joinedload(Bid.seller),
                defer(Bid.source_payload),
                defer(Bid.provenance)
            )
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Apply price filter from choice_answers
    row.bids = [b for b in row.bids if not b.is_superseded]
    row.bids = filter_bids_by_price(row)

    active_deals = await _load_active_deal_summaries(session, [row])
    return _serialize_row(row, active_deals.get(row.id))


@router.delete("/rows/{row_id}")
async def delete_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    row.status = "archived"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"status": "archived", "id": row_id}


@router.patch("/rows/{row_id}")
async def update_row(
    row_id: int,
    row_update: RowUpdate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    print(f"Received PATCH request for row {row_id} with data: {row_update}")
    
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()

    if not row:
        print(f"Row {row_id} not found")
        raise HTTPException(status_code=404, detail="Row not found")
    
    row_data = row_update.dict(exclude_unset=True)
    selected_bid_id = row_data.pop("selected_bid_id", None)
    request_spec_updates = row_data.pop("request_spec", None)
    regenerate_choice_factors = row_data.pop("regenerate_choice_factors", None)
    reset_bids = row_data.pop("reset_bids", None)

    if selected_bid_id is not None:
        bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id, Bid.is_superseded == False))
        bids = bids_result.all()
        found = False
        for row_bid in bids:
            if row_bid.id == selected_bid_id:
                found = True
            row_bid.is_selected = row_bid.id == selected_bid_id
            session.add(row_bid)

        if not found:
            raise HTTPException(status_code=404, detail="Option not found")

        row.status = "closed"

    if reset_bids:
        from sqlalchemy import update as sql_update
        await session.exec(
            sql_update(Bid).where(
                Bid.row_id == row_id,
                Bid.is_superseded == False,
            ).values(is_superseded=True, superseded_at=datetime.utcnow())
        )

    # JSONB columns need native dicts/lists, not JSON strings
    jsonb_fields = {"choice_factors", "choice_answers", "search_intent", "provider_query_map", "chat_history"}
    for key, value in row_data.items():
        if key in jsonb_fields and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        setattr(row, key, value)

    if regenerate_choice_factors:
        try:
            from services.llm import generate_choice_factors as _gen_factors
            constraints_obj = {}
            if row.choice_answers:
                constraints_obj = safe_json_loads(row.choice_answers, {})
            item_name = row.title or "product"
            factors = await _gen_factors(
                item_name, constraints_obj,
                row.is_service or False, row.service_category,
            )
            if factors:
                row.choice_factors = factors
            else:
                row.choice_factors = _default_choice_factors_for_row(row)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to regenerate choice factors: {e}")
            row.choice_factors = _default_choice_factors_for_row(row)
        
    if request_spec_updates:
        result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
        spec = result.first()
        if spec:
            spec_data = request_spec_updates
            for key, value in spec_data.items():
                setattr(spec, key, value)
            session.add(spec)

    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    print(f"Row {row_id} updated successfully: {row}")

    # Post-update safety check if title changed
    if "title" in row_data:
        check = SafetyService.check_safety(row.title)
        answers = safe_json_loads(row.choice_answers, {})
        
        # Only update if status changed to avoid loops
        current_status = answers.get("safety_status")
        if check["status"] != "safe" or current_status:
            answers["safety_status"] = check["status"]
            answers["safety_reason"] = check["reason"]
            row.choice_answers = answers
            session.add(row)
            await session.commit()

    return row


@router.post("/rows/{row_id}/options/{option_id}/select")
async def select_row_option(
    row_id: int,
    option_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    bid_result = await session.exec(
        select(Bid).where(Bid.id == option_id, Bid.row_id == row_id)
    )
    bid = bid_result.first()
    if not bid:
        raise HTTPException(status_code=404, detail="Option not found")

    all_bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for row_bid in all_bids_result.all():
        row_bid.is_selected = row_bid.id == option_id
        session.add(row_bid)

    row.status = "closed"
    row.updated_at = datetime.utcnow()
    session.add(row)

    await session.commit()

    return {
        "status": "selected",
        "row_id": row_id,
        "option_id": option_id,
        "row_status": row.status,
    }


@router.post("/rows/{row_id}/duplicate", response_model=Row)
async def duplicate_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Duplicate a row: copies title, choice answers, and constraints into a fresh row.

    Does NOT copy bids, comments, likes, or selected state.
    """
    user_id, is_guest = await resolve_user_id_and_guest_flag(authorization, session)

    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Row not found")

    if is_guest:
        if not x_anonymous_session_id or row.anonymous_session_id != x_anonymous_session_id:
            raise HTTPException(status_code=404, detail="Row not found")

    new_row = Row(
        title=row.title,
        status="open",
        user_id=user_id,
        project_id=row.project_id,
        choice_factors=row.choice_factors,
        choice_answers=row.choice_answers,
        budget_max=row.budget_max,
        currency=row.currency,
        is_service=row.is_service,
        service_category=row.service_category,
        search_intent=row.search_intent,
        structured_constraints=row.structured_constraints,
        anonymous_session_id=row.anonymous_session_id if is_guest else None,
    )
    session.add(new_row)
    await session.commit()
    await session.refresh(new_row)
    return new_row


class ClaimRowsRequest(BaseModel):
    row_ids: List[int]


@router.post("/rows/claim")
async def claim_rows(
    body: ClaimRowsRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Transfer guest-owned rows to the authenticated user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated — claim requires login")

    if not body.row_ids:
        return {"claimed": 0}

    # Find the guest user
    guest_result = await session.exec(
        select(User).where(User.email == GUEST_EMAIL)
    )
    guest_user = guest_result.first()
    if not guest_user:
        return {"claimed": 0}

    # Only claim rows that belong to the guest user
    rows_result = await session.exec(
        select(Row).where(
            Row.id.in_(body.row_ids),
            Row.user_id == guest_user.id,
        )
    )
    rows_to_claim = rows_result.all()

    for row in rows_to_claim:
        row.user_id = auth_session.user_id  # transfer from guest to real user
        row.updated_at = datetime.utcnow()
        session.add(row)

    await session.commit()
    return {"claimed": len(rows_to_claim)}
