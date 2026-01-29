"""Rows routes - CRUD for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_session
from models import Row, RowBase, RowCreate, RequestSpec, Bid, Project
from routes.rows_search import router as rows_search_router

router = APIRouter(tags=["rows"])
router.include_router(rows_search_router)


class SellerRead(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None


class BidRead(BaseModel):
    id: int
    price: float
    currency: str
    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    is_selected: bool = False
    seller: Optional[SellerRead] = None


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


@router.post("/rows", response_model=Row)
async def create_row(
    row: RowCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if row.project_id is not None:
        project = await session.get(Project, row.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="Project not found")
        if project.user_id != auth_session.user_id:
            raise HTTPException(status_code=403, detail="Project not owned by user")

    request_spec_data = row.request_spec
    
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency,
        user_id=auth_session.user_id,
        project_id=row.project_id,
        choice_factors=row.choice_factors,
        choice_answers=row.choice_answers
    )
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
    
    await session.refresh(db_row)
    return db_row


@router.get("/rows", response_model=List[RowReadWithBids])
async def read_rows(
    authorization: Optional[str] = Header(None),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Row)
        .where(
            Row.user_id == auth_session.user_id,
            True if include_archived else (Row.status != "archived"),
        )
        .options(selectinload(Row.bids).joinedload(Bid.seller))
        .order_by(Row.updated_at.desc())
    )
    return result.all()


@router.get("/rows/{row_id}", response_model=RowReadWithBids)
async def read_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Row)
        .where(Row.id == row_id, Row.user_id == auth_session.user_id)
        .options(selectinload(Row.bids).joinedload(Bid.seller))
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row


@router.delete("/rows/{row_id}")
async def delete_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
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
    from routes.auth import get_current_session
    
    print(f"Received PATCH request for row {row_id} with data: {row_update}")
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()

    if not row:
        print(f"Row {row_id} not found")
        raise HTTPException(status_code=404, detail="Row not found")
    
    row_data = row_update.dict(exclude_unset=True)
    selected_bid_id = row_data.pop("selected_bid_id", None)
    request_spec_updates = row_data.pop("request_spec", None)

    if selected_bid_id is not None:
        bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id))
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

    for key, value in row_data.items():
        setattr(row, key, value)
        
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
    return row


@router.post("/rows/{row_id}/options/{option_id}/select")
async def select_row_option(
    row_id: int,
    option_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
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


class CustomBidCreate(BaseModel):
    url: str
    title: Optional[str] = None
    price: Optional[float] = None
    merchant: Optional[str] = None
    image_url: Optional[str] = None


@router.post("/rows/{row_id}/custom-bids", response_model=BidRead)
async def create_custom_bid(
    row_id: int,
    bid_data: CustomBidCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Create a custom bid from a user-provided URL."""
    from routes.auth import get_current_session
    from models import Seller

    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify the row exists and belongs to the user
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Extract merchant domain from URL if not provided
    merchant_name = bid_data.merchant
    merchant_domain = None

    if bid_data.url:
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(bid_data.url)
            merchant_domain = parsed_url.netloc or None
            if not merchant_name:
                # Use domain as fallback merchant name
                merchant_name = merchant_domain or "Custom"
        except Exception:
            merchant_name = merchant_name or "Custom"

    # Find or create seller
    seller = None
    if merchant_domain:
        seller_result = await session.exec(
            select(Seller).where(Seller.domain == merchant_domain)
        )
        seller = seller_result.first()

        if not seller:
            seller = Seller(
                name=merchant_name or merchant_domain,
                domain=merchant_domain
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

    # Create the bid
    price_value = bid_data.price if bid_data.price is not None else 0.0
    db_bid = Bid(
        row_id=row_id,
        seller_id=seller.id if seller else None,
        price=price_value,
        shipping_cost=0.0,
        total_cost=price_value,
        currency="USD",
        item_title=bid_data.title or "Custom Offer",
        item_url=bid_data.url,
        image_url=bid_data.image_url,
        source="manual",
        is_selected=False
    )

    session.add(db_bid)
    await session.commit()
    await session.refresh(db_bid)

    # Load seller relationship for response
    if db_bid.seller_id:
        await session.refresh(db_bid, ["seller"])

    # Return in BidRead format
    return BidRead(
        id=db_bid.id,
        price=db_bid.price,
        currency=db_bid.currency,
        item_title=db_bid.item_title,
        item_url=db_bid.item_url,
        image_url=db_bid.image_url,
        source=db_bid.source,
        is_selected=db_bid.is_selected,
        seller=SellerRead(
            id=seller.id,
            name=seller.name,
            domain=seller.domain
        ) if seller else None
    )
