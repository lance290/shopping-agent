"""Rows routes - CRUD and search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import re
import json
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from database import get_session
from models import Row, RowBase, RowCreate, RequestSpec, Bid, Seller, Project
from sourcing import SourcingRepository, SearchResult

router = APIRouter(tags=["rows"])
logger = logging.getLogger(__name__)

# Lazy init sourcing repository to ensure env vars are loaded
_sourcing_repo = None

def get_sourcing_repo():
    global _sourcing_repo
    if _sourcing_repo is None:
        _sourcing_repo = SourcingRepository()
    return _sourcing_repo


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
    selected_bid_id: Optional[int] = None


class RowSearchRequest(BaseModel):
    query: Optional[str] = None
    providers: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


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
        if not project or project.user_id != auth_session.user_id:
            row.project_id = None

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


@router.post("/rows/{row_id}/search", response_model=SearchResponse)
async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    from routes.rate_limit import check_rate_limit
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    rate_key = f"search:{auth_session.user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()

    base_query = body.query or row.title or (spec.item_name if spec else "")
    logger.info(f"[SEARCH DEBUG] body.query={body.query!r}, row.title={row.title!r}, base_query={base_query!r}")

    if not body.query:
        if spec and spec.constraints:
            try:
                constraints_obj = json.loads(spec.constraints)
                constraint_parts = []
                for k, v in constraints_obj.items():
                    constraint_parts.append(f"{k}: {v}")
                if constraint_parts:
                    base_query = base_query + " " + " ".join(constraint_parts)
            except Exception:
                pass

        if row.choice_answers:
            try:
                answers_obj = json.loads(row.choice_answers)
                answer_parts = []

                def _to_num(v):
                    if v is None or v == "":
                        return None
                    try:
                        return float(v)
                    except Exception:
                        return None

                min_price = _to_num(answers_obj.get('min_price'))
                max_price = _to_num(answers_obj.get('max_price'))
                if min_price is not None or max_price is not None:
                    if min_price is not None and max_price is not None:
                        answer_parts.append(f"price between {min_price} and {max_price}")
                    elif max_price is not None:
                        answer_parts.append(f"price under {max_price}")
                    else:
                        answer_parts.append(f"price over {min_price}")

                for k, v in answers_obj.items():
                    if k in ('min_price', 'max_price'):
                        continue
                    if v and str(v).lower() != "not answered":
                        answer_parts.append(f"{k} {v}")
                if answer_parts:
                    base_query = base_query + " " + " ".join(answer_parts)
            except Exception:
                pass

    # Sanitize: remove price patterns that confuse Amazon search
    clean_query = re.sub(r'\$\d+', '', base_query)
    clean_query = re.sub(r'\b(over|under|below|above)\s*\$?\d+\b', '', clean_query, flags=re.IGNORECASE)
    sanitized_query = " ".join(clean_query.replace("(", " ").replace(")", " ").split())
    sanitized_query = " ".join(sanitized_query.split()[:8]).strip()
    if not sanitized_query:
        sanitized_query = base_query.strip()
    logger.info(f"[SEARCH DEBUG] base_query={base_query!r}, sanitized_query={sanitized_query!r}")

    results = await get_sourcing_repo().search_all(sanitized_query, providers=body.providers)

    # Filter results by price constraints from choice_answers
    min_price_filter = None
    max_price_filter = None
    if row.choice_answers:
        try:
            answers_obj = json.loads(row.choice_answers)
            if answers_obj.get('min_price'):
                min_price_filter = float(answers_obj['min_price'])
            if answers_obj.get('max_price'):
                max_price_filter = float(answers_obj['max_price'])
        except Exception:
            pass
    
    if min_price_filter is not None or max_price_filter is not None:
        filtered_results = []
        for r in results:
            price = getattr(r, 'price', None)
            if price is None:
                filtered_results.append(r)  # Keep items without price
                continue
            if min_price_filter is not None and price <= min_price_filter:
                continue  # "over $X" means strictly greater than X
            if max_price_filter is not None and price > max_price_filter:
                continue
            filtered_results.append(r)
        logger.info(f"[SEARCH] Filtered {len(results)} -> {len(filtered_results)} results (min={min_price_filter}, max={max_price_filter})")
        results = filtered_results

    for r in results:
        try:
            if getattr(r, "click_url", "") and "row_id=" not in str(r.click_url):
                joiner = "&" if "?" in str(r.click_url) else "?"
                r.click_url = f"{r.click_url}{joiner}row_id={row_id}"
        except Exception:
            pass
    
    # Clear old bids and save new results
    existing_bids = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for bid in existing_bids.all():
        await session.delete(bid)
    
    for res in results:
        merchant_name = res.merchant or "Unknown"
        seller_res = await session.exec(select(Seller).where(Seller.name == merchant_name))
        seller = seller_res.first()
        
        if not seller:
            seller = Seller(name=merchant_name, domain=res.merchant_domain)
            session.add(seller)
            await session.commit()
            await session.refresh(seller)
            
        bid = Bid(
            row_id=row_id,
            seller_id=seller.id,
            price=res.price,
            total_cost=res.price,
            currency=res.currency,
            item_title=res.title,
            item_url=res.url,
            image_url=res.image_url,
            source=res.source,
            is_selected=False
        )
        session.add(bid)
        await session.flush()
        res.bid_id = bid.id
        res.is_selected = bid.is_selected
    
    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)
    
    await session.commit()
    
    return {"results": results}
