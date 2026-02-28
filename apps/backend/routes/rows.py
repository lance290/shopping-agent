"""Rows routes - CRUD for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import json
import sqlalchemy as sa

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, defer, joinedload

from database import get_session
from models import Row, RowBase, RowCreate, RequestSpec, Bid, Project, User
from dependencies import get_current_session, resolve_user_id, require_auth, GUEST_EMAIL
from routes.rows_search import router as rows_search_router
from sourcing.safety import SafetyService
from utils.json_utils import safe_json_loads
from services.email import send_admin_vendor_alert

router = APIRouter(tags=["rows"])
router.include_router(rows_search_router)



class SellerRead(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None


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
    combined_score: Optional[float] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    seller: Optional[SellerRead] = None
    provenance: Optional[str] = None


class RowReadWithBids(RowBase):
    id: int
    user_id: int
    project_id: Optional[int] = None
    bids: List[BidRead] = []


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
    provider_query: Optional[str] = None
    selected_bid_id: Optional[int] = None
    regenerate_choice_factors: Optional[bool] = None
    chat_history: Optional[str] = None
    reset_bids: Optional[bool] = None
    is_service: Optional[bool] = None
    service_category: Optional[str] = None
    selected_providers: Optional[str] = None


def _default_choice_factors_for_row(row: Row) -> str:
    """Return empty factors — LLM generates proper contextual factors via regenerate_choice_factors."""
    return "[]"


@router.post("/rows", response_model=Row)
async def create_row(
    row: RowCreate,
    authorization: Optional[str] = Header(None),
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
            db_row.choice_answers = json.dumps(answers)

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


class ClaimRowsRequest(BaseModel):
    row_ids: List[int]

    @field_validator("row_ids")
    @classmethod
    def limit_row_ids(cls, v: List[int]) -> List[int]:
        if len(v) > 100:
            raise ValueError("Cannot claim more than 100 rows at once")
        return v


@router.post("/rows/claim")
async def claim_guest_rows(
    body: ClaimRowsRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Migrate anonymous (guest) rows to the authenticated user.

    Called after login/register so the user keeps their anonymous search
    results, bids, and selections.
    """
    auth_session = await require_auth(authorization, session)
    user_id = auth_session.user_id

    if not body.row_ids:
        return {"claimed": 0}

    # Look up the guest user — bail early if it doesn't exist
    guest_result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
    guest_user = guest_result.first()
    if not guest_user:
        return {"claimed": 0}

    # Only claim rows that belong to the guest user (prevent stealing other users' rows)
    stmt = (
        sa.update(Row.__table__)
        .where(Row.id.in_(body.row_ids))  # type: ignore[attr-defined]
        .where(Row.user_id == guest_user.id)
        .values(user_id=user_id)
    )
    result = await session.exec(stmt)
    await session.commit()

    claimed = result.rowcount  # type: ignore[union-attr]
    print(f"[ROWS] Claimed {claimed} guest rows for user {user_id}")
    return {"claimed": claimed}


@router.get("/rows", response_model=List[RowReadWithBids])
async def read_rows(
    authorization: Optional[str] = Header(None),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        return []  # Anonymous users see empty board (guest rows are shared)

    result = await session.exec(
        select(Row)
        .where(
            Row.user_id == auth_session.user_id,
            True if include_archived else (Row.status != "archived"),
        )
        .options(
            selectinload(Row.bids).options(
                joinedload(Bid.seller),
                defer(Bid.source_payload)
            )
        )
        .order_by(Row.updated_at.desc())
    )
    rows = result.all()
    for row in rows:
        row.bids = [b for b in row.bids if not b.is_superseded]
    return rows


@router.get("/rows/{row_id}", response_model=RowReadWithBids)
async def read_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Row)
        .where(Row.id == row_id, Row.user_id == user_id)
        .options(
            selectinload(Row.bids).options(
                joinedload(Bid.seller),
                defer(Bid.source_payload)
            )
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    row.bids = [b for b in row.bids if not b.is_superseded]
    
    return row


@router.delete("/rows/{row_id}")
async def delete_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
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
        bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id))
        bids = bids_result.all()
        found = False
        selected_bid = None
        for row_bid in bids:
            if row_bid.id == selected_bid_id:
                found = True
                selected_bid = row_bid
            row_bid.is_selected = row_bid.id == selected_bid_id
            session.add(row_bid)

        if not found:
            raise HTTPException(status_code=404, detail="Option not found")

        row.status = "selected"

        vendor_name = None
        vendor_email = None
        vendor_company = None
        
        # Phase 1 Deal Handoff logic
        if selected_bid:
            selected_bid.closing_status = "selected"
            session.add(selected_bid)
            
            if selected_bid.vendor_id:
                from models import Vendor, DealHandoff, SellerQuote, User
                
                v_result = await session.exec(select(Vendor).where(Vendor.id == selected_bid.vendor_id))
                vendor = v_result.first()
                if vendor:
                    vendor_name = vendor.contact_name or vendor.name
                    vendor_email = vendor.email
                    vendor_company = vendor.name
                    
                    # Look up buyer
                    b_result = await session.exec(select(User).where(User.id == row.user_id))
                    buyer = b_result.first()
                    buyer_email = buyer.email if buyer else "demo@buyanything.ai"
                    
                    # Did this come from a quote?
                    quote_id = None
                    if selected_bid.source == "vendor_quote":
                        q_result = await session.exec(select(SellerQuote).where(SellerQuote.bid_id == selected_bid.id))
                        quote = q_result.first()
                        if quote:
                            quote_id = quote.id
                            quote.status = "accepted"
                            session.add(quote)

                    # Create DealHandoff
                    from models import generate_magic_link_token
                    handoff = DealHandoff(
                        row_id=row.id,
                        bid_id=selected_bid.id,
                        quote_id=quote_id,
                        vendor_id=vendor.id,
                        buyer_user_id=row.user_id,
                        buyer_email=buyer_email,
                        buyer_name=buyer.name if buyer else None,
                        buyer_phone=buyer.phone if buyer else None,
                        vendor_email=vendor_email,
                        vendor_name=vendor_name,
                        deal_value=selected_bid.price,
                        currency=selected_bid.currency or "USD",
                        status="introduced",
                        acceptance_token=generate_magic_link_token(),
                    )
                    session.add(handoff)
                    
                    # Notify vendor
                    if vendor_email:
                        from services.email import send_vendor_selected_email
                        v_result = await send_vendor_selected_email(
                            vendor_email=vendor_email,
                            vendor_name=vendor_name,
                            buyer_name=buyer.name if buyer else None,
                            buyer_email=buyer_email,
                            buyer_phone=buyer.phone if buyer else None,
                            request_summary=row.title,
                            deal_value=selected_bid.price,
                            acceptance_token=handoff.acceptance_token,
                        )
                        if v_result.success:
                            handoff.seller_email_sent_at = datetime.utcnow()

        # Admin alert: a deal was selected
        await send_admin_vendor_alert(
            event_type="deal_selected",
            vendor_name=vendor_name or (selected_bid.item_title if selected_bid else None),
            vendor_email=vendor_email,
            vendor_company=vendor_company,
            row_title=row.title,
            row_id=row_id,
            quote_price=selected_bid.price if selected_bid else None,
        )

    if reset_bids:
        from sqlalchemy import update as sql_update
        await session.exec(
            sql_update(Bid).where(
                Bid.row_id == row_id,
                Bid.is_superseded == False,
            ).values(is_superseded=True, superseded_at=datetime.utcnow())
        )

    for key, value in row_data.items():
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
                row.choice_factors = json.dumps(factors)
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
            row.choice_answers = json.dumps(answers)
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
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
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
