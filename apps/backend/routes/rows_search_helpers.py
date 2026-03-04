from typing import Optional, Any
import json
from models import Row
from pydantic import BaseModel

class RequestSpec(BaseModel):
    item_name: str
    constraints: str = "{}"

def _serialize_json_payload(payload: Optional[Any]) -> Optional[Any]:
    if payload is None:
        return None
    try:
        return json.dumps(payload) if not isinstance(payload, str) else payload
    except Exception:
        return str(payload)

def _parse_intent_payload(payload: Optional[Any]) -> Optional[dict]:
    if not payload:
        return None
    try:
        return json.loads(payload) if isinstance(payload, str) else payload
    except Exception:
        return None

def _extract_filters(row: Row, spec: Optional[RequestSpec]) -> tuple[Optional[float], Optional[float], dict]:
    try:
        ans = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
    except Exception:
        ans = {}
    if not isinstance(ans, dict):
        ans = {}

    min_p, max_p = None, None
    for k in ("min_price", "price_min", "minimum_price"):
        if k in ans:
            try:
                min_p = float(ans[k])
                break
            except Exception:
                pass
    for k in ("max_price", "price_max", "maximum_price", "budget"):
        if k in ans:
            try:
                max_p = float(ans[k])
                break
            except Exception:
                pass

    try:
        c = json.loads(spec.constraints) if spec and spec.constraints else {}
    except Exception:
        c = {}
    if isinstance(c, dict):
        for k in ("max_price", "budget"):
            if k in c and max_p is None:
                try:
                    max_p = float(c[k])
                except Exception:
                    pass
        for k in ("min_price", "minimum_price"):
            if k in c and min_p is None:
                try:
                    min_p = float(c[k])
                except Exception:
                    pass

    return min_p, max_p, ans

def _build_base_query(row: Row, spec: Optional[RequestSpec], explicit_query: Optional[str]) -> tuple[str, bool]:
    user_provided = False
    if explicit_query and explicit_query.strip():
        return explicit_query.strip(), True
    if row.provider_query and row.provider_query.strip():
        return row.provider_query.strip(), False
    if spec and spec.item_name:
        user_provided = True
        return spec.item_name.strip(), True
    return row.title or "product", False

def _sanitize_query(base_query: str, user_provided: bool) -> str:
    if len(base_query) > 150:
        base_query = base_query[:150]
    return base_query.strip()
