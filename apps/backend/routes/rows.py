"""Rows routes - CRUD for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Any, Optional, List
from datetime import datetime
import json
from urllib.parse import urlparse

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, defer, joinedload

from database import get_session
from models import Row, RowBase, RowCreate, RequestSpec, Bid, Project, User, Vendor, RequestFeedback, RequestEvent, SourceMemory
from models.deals import Deal, DealMessage
from models.bookmarks import VendorBookmark, ItemBookmark
from models.outreach import OutreachMessage
from dependencies import get_current_session, resolve_user_id, resolve_user_id_and_guest_flag, GUEST_EMAIL
from routes.rows_search import router as rows_search_router
from routes.bookmarks import _normalize_bookmark_url
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
    canonical_url: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    is_selected: bool = False
    is_liked: bool = False
    liked_at: Optional[datetime] = None
    is_service_provider: bool = False
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    vendor_id: Optional[int] = None
    seller: Optional[SellerRead] = None
    is_vendor_bookmarked: bool = False
    is_item_bookmarked: bool = False
    is_emailed: bool = False


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


class RowOutcomeUpdate(BaseModel):
    outcome: Optional[str] = None  # resolution: solved, partially_solved, not_solved
    quality: Optional[str] = None  # quality: results_were_strong, results_were_noisy, had_to_search_manually, routing_was_wrong
    note: Optional[str] = None


class RequestFeedbackCreate(BaseModel):
    bid_id: Optional[int] = None
    feedback_type: str
    score: Optional[float] = None
    comment: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class RequestEventCreate(BaseModel):
    bid_id: Optional[int] = None
    event_type: str
    event_value: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


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


async def _load_bookmark_state_for_bids(
    session: AsyncSession, user_id: int, rows: List[Row],
) -> tuple[set[int], set[str], set[int]]:
    """Return (bookmarked_vendor_ids, bookmarked_item_urls, emailed_bid_ids) for the given user and rows."""
    all_vendor_ids: set[int] = set()
    all_item_urls: set[str] = set()
    row_ids: list[int] = []
    for row in rows:
        row_ids.append(row.id)
        for bid in (row.bids or []):
            if bid.vendor_id:
                all_vendor_ids.add(bid.vendor_id)
            bookmark_url = _normalize_bookmark_url(bid.canonical_url or bid.item_url)
            if bookmark_url:
                all_item_urls.add(bookmark_url)

    bookmarked_vendor_ids: set[int] = set()
    if all_vendor_ids:
        bm_result = await session.exec(
            select(VendorBookmark.vendor_id)
            .where(VendorBookmark.user_id == user_id, VendorBookmark.vendor_id.in_(all_vendor_ids))
        )
        bookmarked_vendor_ids = set(bm_result.all())

    bookmarked_item_urls: set[str] = set()
    if all_item_urls:
        item_result = await session.exec(
            select(ItemBookmark.canonical_url)
            .where(ItemBookmark.user_id == user_id, ItemBookmark.canonical_url.in_(all_item_urls))
        )
        bookmarked_item_urls = set(item_result.all())

    emailed_bid_ids: set[int] = set()
    if row_ids:
        om_result = await session.exec(
            select(OutreachMessage.bid_id)
            .where(
                OutreachMessage.bid_id.isnot(None),
                OutreachMessage.status.in_(("sent", "delivered", "replied")),
            )
            .where(OutreachMessage.bid_id.in_(
                select(Bid.id).where(Bid.row_id.in_(row_ids))
            ))
        )
        emailed_bid_ids = {bid_id for bid_id in om_result.all() if bid_id is not None}

    return bookmarked_vendor_ids, bookmarked_item_urls, emailed_bid_ids


def _enrich_bid_dict(
    bid_dict: dict,
    db_bid: Bid,
    bookmarked_vendor_ids: set[int],
    bookmarked_item_urls: set[str],
    emailed_bid_ids: set[int],
) -> dict:
    """Inject vendor state indicators into a serialized bid dict."""
    bookmark_url = _normalize_bookmark_url(db_bid.canonical_url or db_bid.item_url)
    is_vendor_bookmarked = bool(db_bid.vendor_id and db_bid.vendor_id in bookmarked_vendor_ids)
    is_item_bookmarked = bool(bookmark_url and bookmark_url in bookmarked_item_urls)
    bid_dict["canonical_url"] = db_bid.canonical_url or bookmark_url
    bid_dict["is_vendor_bookmarked"] = is_vendor_bookmarked
    bid_dict["is_item_bookmarked"] = is_item_bookmarked
    bid_dict["is_liked"] = is_vendor_bookmarked or is_item_bookmarked
    bid_dict["is_emailed"] = bool(db_bid.id and db_bid.id in emailed_bid_ids)
    return bid_dict


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
    
    active_deals = await _load_active_deal_summaries(session, rows)
    bookmarked_vendors, bookmarked_items, emailed_bids = await _load_bookmark_state_for_bids(session, user_id, rows)
    
    results = []
    for row in rows:
        from routes.rows_search import _extract_filters
        from sourcing.filters import should_include_result
        min_price, max_price, _ = _extract_filters(row, None)
        
        payload = RowReadWithBids.model_validate(row, from_attributes=True).model_dump()
        payload["active_deal"] = active_deals.get(row.id)
        payload["ui_schema"] = augment_schema_with_active_deal(payload.get("ui_schema"), payload["active_deal"], row)
        
        filtered_bids = []
        for db_bid in row.bids:
            if db_bid.is_superseded:
                continue
                
            source = str(db_bid.source or "").lower()
            if not should_include_result(
                price=db_bid.price,
                source=source,
                desire_tier=row.desire_tier,
                min_price=min_price,
                max_price=max_price,
                is_service_provider=db_bid.is_service_provider,
            ):
                continue
            
            bid_dict = BidRead.model_validate(db_bid, from_attributes=True).model_dump()
            _enrich_bid_dict(bid_dict, db_bid, bookmarked_vendors, bookmarked_items, emailed_bids)
            filtered_bids.append(bid_dict)
            
        payload["bids"] = filtered_bids
        results.append(payload)
        
    return results


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

    if is_guest and row.anonymous_session_id and row.anonymous_session_id != x_anonymous_session_id:
        raise HTTPException(status_code=404, detail="Row not found")
    
    active_deals = await _load_active_deal_summaries(session, [row])
    bookmarked_vendors, bookmarked_items, emailed_bids = await _load_bookmark_state_for_bids(session, user_id, [row])
    
    from routes.rows_search import _extract_filters
    from sourcing.filters import should_include_result
    min_price, max_price, _ = _extract_filters(row, None)
    
    payload = RowReadWithBids.model_validate(row, from_attributes=True).model_dump()
    payload["active_deal"] = active_deals.get(row.id)
    payload["ui_schema"] = augment_schema_with_active_deal(payload.get("ui_schema"), payload["active_deal"], row)
    
    filtered_bids = []
    for db_bid in row.bids:
        if db_bid.is_superseded:
            continue
            
        source = str(db_bid.source or "").lower()
        if not should_include_result(
            price=db_bid.price,
            source=source,
            desire_tier=row.desire_tier,
            min_price=min_price,
            max_price=max_price,
            is_service_provider=db_bid.is_service_provider,
        ):
            continue
        
        bid_dict = BidRead.model_validate(db_bid, from_attributes=True).model_dump()
        _enrich_bid_dict(bid_dict, db_bid, bookmarked_vendors, bookmarked_items, emailed_bids)
        filtered_bids.append(bid_dict)
        
    payload["bids"] = filtered_bids
    return payload


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
        selected_bid: Optional[Bid] = None
        for row_bid in bids:
            if row_bid.id == selected_bid_id:
                found = True
                selected_bid = row_bid
            row_bid.is_selected = row_bid.id == selected_bid_id
            session.add(row_bid)

        if not found:
            raise HTTPException(status_code=404, detail="Option not found")

        row.status = "closed"
        if selected_bid is not None:
            session.add(RequestEvent(
                row_id=row_id,
                bid_id=selected_bid.id,
                user_id=user_id,
                event_type="candidate_selected",
                event_value=selected_bid.source,
            ))

    if reset_bids:
        bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id, Bid.is_superseded == False))
        for b in bids_result.all():
            b.is_superseded = True
            b.superseded_at = datetime.utcnow()
            session.add(b)

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


@router.post("/rows/{row_id}/feedback")
async def create_row_feedback(
    row_id: int,
    body: RequestFeedbackCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if body.bid_id is not None:
        bid_result = await session.exec(
            select(Bid).where(Bid.id == body.bid_id, Bid.row_id == row_id)
        )
        bid = bid_result.first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")

    feedback = RequestFeedback(
        row_id=row_id,
        bid_id=body.bid_id,
        user_id=user_id,
        feedback_type=body.feedback_type,
        score=body.score,
        comment=body.comment,
        metadata_json=json.dumps(body.metadata) if body.metadata is not None else None,
    )
    session.add(feedback)

    event = RequestEvent(
        row_id=row_id,
        bid_id=body.bid_id,
        user_id=user_id,
        event_type="feedback_submitted",
        event_value=body.feedback_type,
        metadata_json=json.dumps(
            {
                "score": body.score,
                "has_comment": bool((body.comment or "").strip()),
            }
        ),
    )
    session.add(event)
    await session.commit()
    await session.refresh(feedback)

    return {"id": feedback.id, "status": "ok"}


@router.post("/rows/{row_id}/outcome")
async def record_row_outcome(
    row_id: int,
    body: RowOutcomeUpdate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    VALID_RESOLUTIONS = {"solved", "partially_solved", "not_solved"}
    VALID_QUALITY = {
        "results_were_strong", "results_were_noisy",
        "had_to_search_manually", "routing_was_wrong",
    }

    if body.outcome is None and body.quality is None:
        raise HTTPException(
            status_code=422,
            detail="At least one of outcome or quality must be provided",
        )

    if body.outcome is not None and body.outcome not in VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"outcome must be one of: {', '.join(sorted(VALID_RESOLUTIONS))}",
        )
    if body.quality is not None and body.quality not in VALID_QUALITY:
        raise HTTPException(
            status_code=422,
            detail=f"quality must be one of: {', '.join(sorted(VALID_QUALITY))}",
        )

    if body.outcome is not None:
        row.row_outcome = body.outcome
    if body.quality is not None:
        row.row_quality_assessment = body.quality
    if body.note is not None:
        row.outcome_note = body.note
    row.updated_at = datetime.utcnow()
    session.add(row)

    event_meta: dict = {}
    if body.outcome:
        event_meta["outcome"] = body.outcome
    if body.quality:
        event_meta["quality"] = body.quality
    if body.note:
        event_meta["note"] = body.note

    event = RequestEvent(
        row_id=row_id,
        user_id=user_id,
        event_type="outcome_recorded",
        event_value=body.outcome or body.quality,
        metadata_json=json.dumps(event_meta) if event_meta else None,
    )
    session.add(event)
    await session.commit()

    # Source memory write-back (PRD §11.3, Tech Spec §8.1)
    if body.outcome in ("solved", "partially_solved", "not_solved"):
        try:
            await _update_source_memory(session, row_id, user_id, body.outcome)
        except Exception:
            pass  # Non-fatal: don't block outcome response

    return {
        "row_id": row_id,
        "outcome": row.row_outcome,
        "quality": row.row_quality_assessment,
        "status": "ok",
    }


async def _update_source_memory(
    session: AsyncSession, row_id: int, user_id: Optional[int], outcome: str
) -> None:
    row_result = await session.exec(
        select(Row)
        .where(Row.id == row_id)
        .options(selectinload(Row.bids))
    )
    row = row_result.first()
    if not row or not row.bids:
        return

    is_success = outcome in ("solved", "partially_solved")
    bookmarked_vendor_ids: set[int] = set()
    bookmarked_item_urls: set[str] = set()
    emailed_bid_ids: set[int] = set()

    if user_id is not None:
        (
            bookmarked_vendor_ids,
            bookmarked_item_urls,
            emailed_bid_ids,
        ) = await _load_bookmark_state_for_bids(session, user_id, [row])

    now = datetime.utcnow()
    aggregates: dict[tuple[str, Optional[str], Optional[str]], dict[str, int]] = {}

    for bid in row.bids:
        domain = _source_memory_domain_for_bid(bid)
        if not domain:
            continue
        source_type = bid.source or None
        source_subtype = bid.source_tier
        key = (domain, source_type, source_subtype)
        if key not in aggregates:
            aggregates[key] = {
                "surface": 0,
                "shortlist": 0,
                "selected": 0,
                "contacted": 0,
            }

        bookmark_url = _normalize_bookmark_url(bid.canonical_url or bid.item_url)
        is_shortlisted = (
            bid.is_liked
            or bool(bid.vendor_id and bid.vendor_id in bookmarked_vendor_ids)
            or bool(bookmark_url and bookmark_url in bookmarked_item_urls)
        )

        aggregates[key]["surface"] += 1
        if is_shortlisted:
            aggregates[key]["shortlist"] += 1
        if bid.is_selected:
            aggregates[key]["selected"] += 1
        if bid.id is not None and bid.id in emailed_bid_ids:
            aggregates[key]["contacted"] += 1

    for (domain, source_type, source_subtype), counts in aggregates.items():
        existing = await session.exec(
            select(SourceMemory).where(
                SourceMemory.domain == domain,
                SourceMemory.source_type == source_type,
                SourceMemory.source_subtype == source_subtype,
            )
        )
        mem = existing.first()
        success_delta = counts["selected"] if is_success else 0
        negative_delta = counts["surface"] if outcome == "not_solved" else 0
        if mem:
            mem.surface_count += counts["surface"]
            mem.shortlist_count += counts["shortlist"]
            mem.contact_success_count += counts["contacted"]
            mem.success_count += success_delta
            mem.negative_count += negative_delta
            mem.last_seen_at = now
            mem.updated_at = now
        else:
            mem = SourceMemory(
                domain=domain,
                source_type=source_type,
                source_subtype=source_subtype,
                surface_count=counts["surface"],
                success_count=success_delta,
                negative_count=negative_delta,
                shortlist_count=counts["shortlist"],
                contact_success_count=counts["contacted"],
                last_seen_at=now,
                updated_at=now,
            )
        mem.trust_score = round(mem.success_count / max(mem.surface_count, 1), 4)
        session.add(mem)

    await session.commit()


def _source_memory_domain_for_bid(bid: Bid) -> Optional[str]:
    merchant_domain = getattr(bid, "merchant_domain", None)
    if merchant_domain:
        return merchant_domain.lower()
    for candidate_url in (getattr(bid, "canonical_url", None), getattr(bid, "item_url", None)):
        if not candidate_url:
            continue
        parsed = urlparse(candidate_url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            return host
    if bid.source:
        return bid.source.lower()
    return None


@router.post("/rows/{row_id}/events")
async def create_row_event(
    row_id: int,
    body: RequestEventCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if body.bid_id is not None:
        bid_result = await session.exec(
            select(Bid).where(Bid.id == body.bid_id, Bid.row_id == row_id)
        )
        bid = bid_result.first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")

    event = RequestEvent(
        row_id=row_id,
        bid_id=body.bid_id,
        user_id=user_id,
        event_type=body.event_type,
        event_value=body.event_value,
        metadata_json=json.dumps(body.metadata) if body.metadata is not None else None,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    return {"id": event.id, "status": "ok"}


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

    # Trust event: candidate_selected (PRD §7.2 — acted on)
    session.add(RequestEvent(
        row_id=row_id,
        bid_id=option_id,
        user_id=user_id,
        event_type="candidate_selected",
        event_value=bid.source,
    ))

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
