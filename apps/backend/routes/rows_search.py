"""Rows search routes - sourcing/search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import re
import json
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, RequestSpec, Bid, Seller
from sourcing import (
    SourcingRepository,
    SearchResult,
    SearchIntent,
    build_provider_query_map,
    available_provider_ids,
)

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
    search_intent: Optional[Any] = None
    provider_query_map: Optional[Any] = None


def _serialize_json_payload(payload: Optional[Any]) -> Optional[str]:
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload)
    except TypeError:
        return json.dumps(payload, default=str)


def _parse_intent_payload(payload: Optional[Any]) -> Optional[SearchIntent]:
    if payload is None:
        return None
    if isinstance(payload, SearchIntent):
        return payload
    data = payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
    try:
        return SearchIntent.model_validate(data)
    except Exception:
        return None


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

    base_query = body.query or row.provider_query or row.title or (spec.item_name if spec else "")
    user_provided_query = bool(body.query)  # Track if query was explicitly provided by user
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

    # Only truncate if query was NOT explicitly provided by user
    # When user provides explicit search query, preserve it fully (after sanitization)
    if not user_provided_query:
        # For auto-constructed queries (with constraints/answers), limit to 12 words to keep focused
        sanitized_query = " ".join(sanitized_query.split()[:12]).strip()

    if not sanitized_query:
        sanitized_query = base_query.strip()
    logger.info(f"[SEARCH DEBUG] base_query={base_query!r}, sanitized_query={sanitized_query!r}")

    if body.search_intent is not None or body.provider_query_map is not None:
        parsed_intent = _parse_intent_payload(body.search_intent)
        row.search_intent = _serialize_json_payload(
            parsed_intent.model_dump() if parsed_intent else body.search_intent
        )
        if body.provider_query_map is not None:
            row.provider_query_map = _serialize_json_payload(body.provider_query_map)
        elif parsed_intent:
            provider_ids = body.providers or available_provider_ids()
            query_map = build_provider_query_map(parsed_intent, provider_ids)
            row.provider_query_map = _serialize_json_payload(query_map.model_dump())
        row.updated_at = datetime.utcnow()
        session.add(row)
        await session.commit()

    search_response = await get_sourcing_repo().search_all_with_status(sanitized_query, providers=body.providers)
    results = search_response.results
    user_message = search_response.user_message

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
            logger.info(f"[SEARCH] choice_answers for row {row_id}: {answers_obj}")
            if answers_obj.get("min_price"):
                min_price_filter = float(answers_obj["min_price"])
            if answers_obj.get("max_price"):
                max_price_filter = float(answers_obj["max_price"])
            # Swap if inverted (min > max)
            if min_price_filter is not None and max_price_filter is not None and min_price_filter > max_price_filter:
                logger.warning(f"[SEARCH] Inverted price range detected (min={min_price_filter} > max={max_price_filter}), swapping")
                min_price_filter, max_price_filter = max_price_filter, min_price_filter
        except Exception as e:
            logger.error(f"[SEARCH] Failed to parse choice_answers: {e}")
    else:
        logger.info(f"[SEARCH] No choice_answers for row {row_id}")

    if min_price_filter is not None or max_price_filter is not None:
        filtered_results = []
        for r in results:
            price = getattr(r, "price", None)
            # Keep items with unknown price (None or 0) - don't filter them out
            if price is None or price == 0:
                filtered_results.append(r)
                continue
            # Filter: keep items where price >= min AND price <= max
            if min_price_filter is not None and price < min_price_filter:
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
    existing_bids_list = existing_bids.all()
    existing_bids_map = {bid.item_url: bid for bid in existing_bids_list if bid.item_url}
    logger.info(f"[SEARCH] Row {row_id}: {len(existing_bids_list)} existing bids, {len(results)} new results to process")

    new_bids_created = 0
    bids_updated = 0
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
            bids_updated += 1
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
            new_bids_created += 1

    logger.info(f"[SEARCH] Row {row_id}: created {new_bids_created} new bids, updated {bids_updated} existing bids")
    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)

    await session.commit()

    response = {"results": results}
    if user_message:
        response["user_message"] = user_message
    return response
