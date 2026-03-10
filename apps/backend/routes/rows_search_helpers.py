import re
import json
from typing import Optional, Any
from models import Row, RequestSpec
from sourcing.location import normalize_search_intent_payload
from sourcing.choice_filter import extract_choice_constraints
from sourcing.models import SearchIntent
from utils.json_utils import safe_json_loads

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
