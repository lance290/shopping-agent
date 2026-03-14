import re
import json
import logging
from typing import Optional, List, Any

from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Row, RequestSpec, Bid, User
from models.bookmarks import VendorBookmark, ItemBookmark
from models.outreach import OutreachMessage
from sourcing import SourcingRepository, SearchResult, ProviderStatusSnapshot
from sourcing.location import normalize_search_intent_payload
from sourcing.choice_filter import extract_choice_constraints
from sourcing.models import SearchIntent
from utils.json_utils import safe_json_loads
from routes.bookmarks import _normalize_bookmark_url

logger = logging.getLogger(__name__)

GUEST_EMAIL = "guest@buy-anything.com"

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


class SearchResponse(BaseModel):
    results: List[SearchResult]
    provider_statuses: List[ProviderStatusSnapshot]
    user_message: Optional[str] = None


async def resolve_user_id_and_guest(authorization: Optional[str], session: AsyncSession) -> tuple[int, bool]:
    from dependencies import resolve_user_id_and_guest_flag
    return await resolve_user_id_and_guest_flag(authorization, session)


async def log_request_event(
    session: AsyncSession,
    *,
    row_id: int,
    user_id: int,
    event_type: str,
    event_value: Optional[str] = None,
    bid_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    from models import RequestEvent
    event = RequestEvent(
        row_id=row_id,
        bid_id=bid_id,
        user_id=user_id,
        event_type=event_type,
        event_value=event_value,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
    )
    session.add(event)


async def load_search_state_for_bids(
    session: AsyncSession,
    user_id: int,
    bids: List[Bid],
) -> tuple[set[int], set[str], set[int]]:
    vendor_ids = {bid.vendor_id for bid in bids if bid.vendor_id}
    item_urls = {
        normalized
        for bid in bids
        if (normalized := _normalize_bookmark_url(bid.canonical_url or bid.item_url))
    }
    bid_ids = {bid.id for bid in bids if bid.id is not None}

    bookmarked_vendor_ids: set[int] = set()
    if vendor_ids:
        result = await session.exec(
            select(VendorBookmark.vendor_id)
            .where(VendorBookmark.user_id == user_id, VendorBookmark.vendor_id.in_(vendor_ids))
        )
        bookmarked_vendor_ids = set(result.all())

    bookmarked_item_urls: set[str] = set()
    if item_urls:
        result = await session.exec(
            select(ItemBookmark.canonical_url)
            .where(ItemBookmark.user_id == user_id, ItemBookmark.canonical_url.in_(item_urls))
        )
        bookmarked_item_urls = set(result.all())

    emailed_bid_ids: set[int] = set()
    if bid_ids:
        result = await session.exec(
            select(OutreachMessage.bid_id)
            .where(
                OutreachMessage.bid_id.isnot(None),
                OutreachMessage.bid_id.in_(bid_ids),
                OutreachMessage.status.in_(("sent", "delivered", "replied")),
            )
        )
        emailed_bid_ids = {bid_id for bid_id in result.all() if bid_id is not None}

    return bookmarked_vendor_ids, bookmarked_item_urls, emailed_bid_ids

def _build_base_query(row: Row, spec: Optional[RequestSpec], explicit_query: Optional[str]) -> tuple[str, bool]:
    """Build the base search query from row data."""
    base_query = explicit_query or row.title or (spec.item_name if spec else "")
    user_provided = bool(explicit_query)
    return base_query, user_provided

def _sanitize_query(base_query: str, user_provided: bool) -> str:
    """Sanitize search query: remove price patterns, truncate if auto-constructed."""
    clean_query = re.sub(r"\$\d+", "", base_query)
    clean_query = re.sub(
        r"\b(over|under|below|above)\s*\$?\d+\b", "", clean_query, flags=re.IGNORECASE
    )
    sanitized = " ".join(clean_query.replace("(", " ").replace(")", " ").split())

    if not user_provided:
        sanitized = " ".join(sanitized.split()[:12]).strip()

    return sanitized if sanitized else base_query.strip()

def _extract_filters(row: Row, spec: Optional[RequestSpec]) -> tuple[Optional[float], Optional[float], dict]:
    """Extract price and choice filters from row.choice_answers and spec.constraints."""
    min_price = None
    max_price = None
    choice_constraints: dict = {}

    def _parse_price_value(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            value_str = str(value).lower().replace('$', '').strip()
            match = re.search(r'(\d[\d,]*(?:\.\d*)?)', value_str)
            if not match:
                return None
            num_str = match.group(1).replace(',', '')
            if not num_str:
                return None
            val = float(num_str)
            if re.search(r'\d[\d,]*(?:\.\d*)?\s*k\b', value_str):
                val *= 1000
            return val
        except Exception:
            return None

    if row.choice_answers:
        answers_obj = safe_json_loads(row.choice_answers, {})
        if isinstance(answers_obj, dict):
            min_price = _parse_price_value(answers_obj.get("min_price"))
            max_price = _parse_price_value(answers_obj.get("max_price"))
            if min_price is None and max_price is None:
                parsed_price = _parse_price_value(answers_obj.get("price"))
                if parsed_price is not None:
                    min_price = parsed_price
            if min_price is not None and max_price is not None and min_price > max_price:
                min_price, max_price = max_price, min_price
            choice_constraints = extract_choice_constraints(row.choice_answers)

    return min_price, max_price, choice_constraints

def _serialize_json_payload(payload: Optional[Any]) -> Optional[Any]:
    """Return native dict/list for JSONB columns. Parse strings if needed."""
    if payload is None:
        return None
    if isinstance(payload, (dict, list)):
        return payload
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return payload
    try:
        return json.loads(json.dumps(payload, default=str))
    except (TypeError, json.JSONDecodeError):
        return str(payload)

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
        normalized = normalize_search_intent_payload(data) if isinstance(data, dict) else data
        return SearchIntent.model_validate(normalized)
    except Exception:
        return None
