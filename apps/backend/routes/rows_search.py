"""Rows search routes - sourcing/search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import re
import json
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, RequestSpec, Bid, Seller
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


class RowSearchRequest(BaseModel):
    query: Optional[str] = None
    providers: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


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
    logger.info(
        f"[SEARCH DEBUG] body.query={body.query!r}, row.title={row.title!r}, base_query={base_query!r}"
    )

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

                min_price = _to_num(answers_obj.get("min_price"))
                max_price = _to_num(answers_obj.get("max_price"))
                if min_price is not None or max_price is not None:
                    if min_price is not None and max_price is not None:
                        answer_parts.append(f"price between {min_price} and {max_price}")
                    elif max_price is not None:
                        answer_parts.append(f"price under {max_price}")
                    else:
                        answer_parts.append(f"price over {min_price}")

                for k, v in answers_obj.items():
                    if k in ("min_price", "max_price"):
                        continue
                    if v and str(v).lower() != "not answered":
                        answer_parts.append(f"{k} {v}")
                if answer_parts:
                    base_query = base_query + " " + " ".join(answer_parts)
            except Exception:
                pass

    # Sanitize: remove price patterns that confuse Amazon search
    clean_query = re.sub(r"\$\d+", "", base_query)
    clean_query = re.sub(
        r"\b(over|under|below|above)\s*\$?\d+\b", "", clean_query, flags=re.IGNORECASE
    )
    sanitized_query = " ".join(clean_query.replace("(", " ").replace(")", " ").split())
    sanitized_query = " ".join(sanitized_query.split()[:8]).strip()
    if not sanitized_query:
        sanitized_query = base_query.strip()
    logger.info(f"[SEARCH DEBUG] base_query={base_query!r}, sanitized_query={sanitized_query!r}")

    results = await get_sourcing_repo().search_all(sanitized_query, providers=body.providers)

    for r in results:
        try:
            if getattr(r, "click_url", "") and "row_id=" not in str(r.click_url):
                joiner = "&" if "?" in str(r.click_url) else "?"
                r.click_url = f"{r.click_url}{joiner}row_id={row_id}"
        except Exception:
            pass

    # Filter results by price constraints from choice_answers
    min_price_filter = None
    max_price_filter = None
    if row.choice_answers:
        try:
            answers_obj = json.loads(row.choice_answers)
            if answers_obj.get("min_price"):
                min_price_filter = float(answers_obj["min_price"])
            if answers_obj.get("max_price"):
                max_price_filter = float(answers_obj["max_price"])
        except Exception:
            pass

    if min_price_filter is not None or max_price_filter is not None:
        filtered_results = []
        for r in results:
            price = getattr(r, "price", None)
            if price is None:
                filtered_results.append(r)
                continue
            if min_price_filter is not None and price <= min_price_filter:
                continue
            if max_price_filter is not None and price > max_price_filter:
                continue
            filtered_results.append(r)
        logger.info(
            f"[SEARCH] Filtered {len(results)} -> {len(filtered_results)} results (min={min_price_filter}, max={max_price_filter})"
        )
        results = filtered_results

    # Keep existing bids but update/add new search results
    # This allows search history to persist across searches
    existing_bids = await session.exec(select(Bid).where(Bid.row_id == row_id))
    existing_bids_map = {bid.item_url: bid for bid in existing_bids.all() if bid.item_url}

    for res in results:
        merchant_name = res.merchant or "Unknown"
        seller_res = await session.exec(select(Seller).where(Seller.name == merchant_name))
        seller = seller_res.first()

        if not seller:
            seller = Seller(name=merchant_name, domain=res.merchant_domain)
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

        # Check if we already have this bid (by URL) - update instead of creating duplicate
        existing_bid = existing_bids_map.get(res.url)
        if existing_bid:
            # Update existing bid with fresh data
            existing_bid.price = res.price
            existing_bid.total_cost = res.price
            existing_bid.currency = res.currency
            existing_bid.item_title = res.title
            existing_bid.image_url = res.image_url
            existing_bid.source = res.source
            existing_bid.seller_id = seller.id
            session.add(existing_bid)
            await session.flush()
            res.bid_id = existing_bid.id
            res.is_selected = existing_bid.is_selected
        else:
            # Create new bid for URLs we haven't seen before
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
                is_selected=False,
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
