"""Helper utilities extracted from SourcingService."""

import json
import logging
import re as _re
from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Row, VendorEndorsement
from sourcing.location import apply_location_resolution, normalize_search_intent_payload
from sourcing.models import SearchIntent
from sourcing.parsers import _parse_numeric, _parse_price_value
from services.location_resolution import LocationResolutionService

logger = logging.getLogger(__name__)

# Key aliases for price constraint extraction — maps normalized key to (role, ...)
_MIN_KEYS = {"min_price", "price_min", "minimum_price", "minimum_value", "minimum value", "minimum price"}
_MAX_KEYS = {"max_price", "price_max", "maximum_price", "maximum_value", "maximum value", "maximum price"}
_RANGE_KEYS = {"price", "budget"}


def extract_vendor_query(row) -> Optional[str]:
    """Extract the clean product name from row.search_intent for vendor search.

    Prefers 'product_name', falls back to 'raw_input'.
    Returns None if no usable intent is found.
    """
    if row is None:
        return None
    raw = getattr(row, "search_intent", None)
    if not raw:
        return None
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    product_name = payload.get("product_name")
    raw_input = payload.get("raw_input")
    location_context = payload.get("location_context") if isinstance(payload.get("location_context"), dict) else {}
    location_mode = str(location_context.get("relevance") or "none")

    def _significant_words(value: object) -> set[str]:
        text = str(value or "").lower()
        return {
            token for token in _re.findall(r"[a-z0-9]+", text)
            if len(token) > 2 and token not in {"the", "and", "for", "with", "from", "into", "your"}
        }

    if product_name:
        if raw_input and location_mode in {"service_area", "vendor_proximity"}:
            product_words = _significant_words(product_name)
            raw_words = _significant_words(raw_input)
            if len(raw_words - product_words) >= 2:
                return str(raw_input)
        return str(product_name)
    if raw_input:
        return str(raw_input)
    return None


def extract_price_constraints(row: Row) -> tuple[Optional[float], Optional[float]]:
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    if row.search_intent:
        try:
            payload = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(payload, dict):
                if payload.get("min_price") is not None:
                    min_price = float(payload["min_price"])
                if payload.get("max_price") is not None:
                    max_price = float(payload["max_price"])
        except Exception:
            pass

    if (min_price is None and max_price is None) and row.choice_answers:
        try:
            answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
            if isinstance(answers, dict):
                # Normalize keys for lookup
                norm = {k.lower().strip(): v for k, v in answers.items()}
                # Direct min keys
                for k in _MIN_KEYS:
                    if k in norm and norm[k] not in (None, ""):
                        val = _parse_numeric(norm[k])
                        if val is not None:
                            min_price = val
                            break
                # Direct max keys
                for k in _MAX_KEYS:
                    if k in norm and norm[k] not in (None, ""):
                        val = _parse_numeric(norm[k])
                        if val is not None:
                            max_price = val
                            break
                # Range/gt/lt from 'price', 'budget', or min/max key values
                if min_price is None and max_price is None:
                    for k in _RANGE_KEYS:
                        if k in norm and norm[k] not in (None, ""):
                            lo, hi = _parse_price_value(norm[k])
                            if lo is not None:
                                min_price = lo
                            if hi is not None:
                                max_price = hi
                            if lo is not None or hi is not None:
                                break
                # Also check min keys for embedded gt/lt (e.g. "minimum value": ">$50")
                if min_price is None:
                    for k in _MIN_KEYS | {"minimum price"}:
                        if k in norm and isinstance(norm[k], str):
                            lo, _ = _parse_price_value(norm[k])
                            if lo is not None:
                                min_price = lo
                                break
        except Exception:
            pass

    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    return min_price, max_price


async def build_endorsement_boosts(session: AsyncSession, user_id: Optional[int]) -> dict[int, float]:
    if not user_id:
        return {}
    stmt = select(VendorEndorsement).where(VendorEndorsement.user_id == user_id)
    result = await session.exec(stmt)
    boosts: dict[int, float] = {}
    for endorsement in result.all():
        rating = int(endorsement.trust_rating or 0)
        base = 0.0
        if rating > 0:
            base += min(rating, 5) * 0.01
        if endorsement.is_personal_contact:
            base += 0.05
        if base > 0:
            boosts[int(endorsement.vendor_id)] = round(min(base, 0.10), 4)
    return boosts


def parse_search_intent(row: Row) -> Optional[SearchIntent]:
    """Parse SearchIntent from row's stored search_intent JSON."""
    if not row or not row.search_intent:
        return None
    try:
        payload = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
        if isinstance(payload, dict):
            normalized = normalize_search_intent_payload(payload)
            return SearchIntent(**normalized)
    except Exception as e:
        logger.debug(f"[SourcingService] Could not parse SearchIntent: {e}")
    return None


async def resolve_search_locations(session: AsyncSession, row: Row, intent: SearchIntent) -> SearchIntent:
    location_context = intent.location_context
    if not location_context or location_context.relevance == "none":
        return intent

    resolver = LocationResolutionService(session)
    resolved_intent = intent
    for field_name, target in location_context.targets.non_empty_items().items():
        current = getattr(resolved_intent.location_resolution, field_name, None)
        if current and current.status == "resolved":
            continue
        try:
            resolution = await resolver.resolve(target)
        except Exception as exc:
            logger.warning("[SourcingService] Location resolution failed for %s=%r: %s", field_name, target, exc)
            continue
        resolved_intent = apply_location_resolution(resolved_intent, field_name, resolution)

    if row.search_intent != resolved_intent.model_dump(mode="json"):
        row.search_intent = resolved_intent.model_dump(mode="json")
        row.updated_at = datetime.utcnow()
        session.add(row)
        await session.commit()
    return resolved_intent
