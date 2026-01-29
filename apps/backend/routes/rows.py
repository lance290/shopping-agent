"""Rows routes - CRUD for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

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
    regenerate_choice_factors: Optional[bool] = None


def _default_choice_factors_for_row(row: Row) -> str:
    title = (getattr(row, "title", "") or "").strip()
    lowered = title.lower()

    base: list[dict] = [
        {
            "name": "condition",
            "label": "Condition",
            "type": "select",
            "options": ["New", "Used", "Refurbished"],
            "required": False,
        },
        {
            "name": "min_price",
            "label": "Min Budget ($)",
            "type": "number",
            "required": False,
        },
        {
            "name": "max_price",
            "label": "Max Budget ($)",
            "type": "number",
            "required": False,
        },
    ]

    if any(k in lowered for k in ("nintendo", "switch", "console", "ps5", "xbox")):
        base.insert(
            0,
            {
                "name": "edition",
                "label": "Edition",
                "type": "select",
                "options": [
                    "Standard",
                    "OLED",
                    "Lite",
                    "Bundle",
                ],
                "required": False,
            },
        )

    return json.dumps(base)


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
    if db_row.choice_factors is None:
        db_row.choice_factors = _default_choice_factors_for_row(db_row)
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
    regenerate_choice_factors = row_data.pop("regenerate_choice_factors", None)

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

    if regenerate_choice_factors:
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
