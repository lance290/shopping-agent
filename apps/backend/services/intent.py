"""
Search intent extraction — heuristic + LLM fallback.

Ported from apps/bff/src/intent/index.ts as part of PRD-02 (Kill BFF).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from services.llm import call_gemini, _extract_json, _get_gemini_api_key

logger = logging.getLogger(__name__)


class SearchIntentResult:
    """Structured search intent for sourcing providers."""

    def __init__(
        self,
        product_category: str = "unknown",
        taxonomy_version: Optional[str] = "v2",
        category_path: Optional[List[str]] = None,
        product_name: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        price_flexibility: Optional[str] = None,
        condition: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        confidence: float = 0.0,
        raw_input: str = "",
        source: str = "heuristic",
        error: Optional[str] = None,
    ):
        self.product_category = product_category
        self.taxonomy_version = taxonomy_version
        self.category_path = category_path or []
        self.product_name = product_name
        self.brand = brand
        self.model = model
        self.min_price = min_price
        self.max_price = max_price
        self.price_flexibility = price_flexibility
        self.condition = condition
        self.features = features or {}
        self.keywords = keywords or []
        self.exclude_keywords = exclude_keywords or []
        self.confidence = confidence
        self.raw_input = raw_input
        self.source = source
        self.error = error

    def to_dict(self) -> dict:
        return {
            "product_category": self.product_category,
            "taxonomy_version": self.taxonomy_version,
            "category_path": self.category_path,
            "product_name": self.product_name,
            "brand": self.brand,
            "model": self.model,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "price_flexibility": self.price_flexibility,
            "condition": self.condition,
            "features": self.features,
            "keywords": self.keywords,
            "exclude_keywords": self.exclude_keywords,
            "confidence": self.confidence,
            "raw_input": self.raw_input,
        }


# =============================================================================
# HEURISTIC HELPERS
# =============================================================================

def _parse_json_object(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _slugify_category(value: str) -> str:
    trimmed = value.strip().lower()
    if not trimmed:
        return "unknown"
    return re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", trimmed))


def _parse_price_constraint(text: str) -> Tuple[Optional[float], Optional[float], str]:
    """Parse price constraints from text. Returns (min, max, remaining_text)."""
    raw = (text or "").strip()
    number_matches = re.findall(r"\$?\s*(\d+(?:\.\d+)?)", raw)
    nums = [float(m) for m in number_matches]

    min_price = None
    max_price = None
    lower = raw.lower()

    if len(nums) >= 2 and re.search(r"\b(to|-)\b", lower):
        min_price = min(nums[0], nums[1])
        max_price = max(nums[0], nums[1])
    elif len(nums) >= 1:
        n = nums[0]
        if re.search(r"(\bover\b|\babove\b|\bmore\b|\bminimum\b|\bat\s*least\b)", lower, re.IGNORECASE):
            min_price = n
        elif re.search(r"(\bunder\b|\bbelow\b|\bless\b|\bmaximum\b|\bat\s*most\b)", lower, re.IGNORECASE):
            max_price = n
        else:
            max_price = n

    remaining = re.sub(r"\$\s*\d+(?:\.\d+)?", "", raw)
    remaining = re.sub(r"\b(over|under|below|above|more|less|at\s+least|at\s+most)\b", "", remaining, flags=re.IGNORECASE)
    remaining = re.sub(r"\b(to)\b", "", remaining, flags=re.IGNORECASE)
    remaining = re.sub(r"[-–—]", " ", remaining)
    remaining = " ".join(remaining.split()).strip()

    return min_price, max_price, remaining


def _extract_keywords(text: str) -> List[str]:
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return list(set(t.strip() for t in tokens if len(t.strip()) > 1))


def _normalize_feature_value(value: Any) -> Any:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value) if value is not None else ""


# =============================================================================
# HEURISTIC INTENT BUILDER
# =============================================================================

def build_heuristic_intent(
    display_query: str,
    row_title: Optional[str] = None,
    choice_answers_json: Optional[str] = None,
    request_spec_constraints_json: Optional[str] = None,
) -> SearchIntentResult:
    """Build a search intent using heuristic rules (no LLM)."""
    raw_input = display_query or row_title or ""
    constraints = _parse_json_object(request_spec_constraints_json)
    choices = _parse_json_object(choice_answers_json)
    price_min, price_max, remaining = _parse_price_constraint(raw_input)

    min_price = choices.get("min_price") or constraints.get("min_price") or price_min
    max_price = choices.get("max_price") or constraints.get("max_price") or price_max
    if min_price is not None:
        min_price = float(min_price)
    if max_price is not None:
        max_price = float(max_price)

    cleaned_query = remaining or raw_input
    product_name = cleaned_query or row_title or raw_input
    product_category = _slugify_category(product_name)
    keywords = _extract_keywords(product_name)

    features: Dict[str, Any] = {}
    for key, value in constraints.items():
        features[key] = _normalize_feature_value(value)
    for key, value in choices.items():
        if key in ("min_price", "max_price"):
            continue
        if key not in features:
            features[key] = _normalize_feature_value(value)

    return SearchIntentResult(
        product_category=product_category or "unknown",
        taxonomy_version="v2",
        category_path=[product_category] if product_category and product_category != "unknown" else [],
        product_name=product_name or None,
        brand=constraints.get("brand") if isinstance(constraints.get("brand"), str) else None,
        model=constraints.get("model") if isinstance(constraints.get("model"), str) else None,
        min_price=min_price,
        max_price=max_price,
        price_flexibility="strict" if (min_price or max_price) else "unknown",
        condition=None,
        features=features,
        keywords=keywords,
        exclude_keywords=[],
        confidence=0.2,
        raw_input=raw_input,
        source="heuristic",
    )


# =============================================================================
# LLM INTENT EXTRACTION
# =============================================================================

async def _extract_intent_with_llm(
    display_query: str,
    row_title: Optional[str] = None,
    project_title: Optional[str] = None,
    choice_answers_json: Optional[str] = None,
    request_spec_constraints_json: Optional[str] = None,
) -> dict:
    """Extract search intent using LLM."""
    prompt = f"""You are extracting a structured SearchIntent JSON for a procurement search.

Output JSON ONLY. No extra text.

Inputs:
- display_query: {json.dumps(display_query or '')}
- row_title: {json.dumps(row_title or '')}
- project_title: {json.dumps(project_title or '')}
- choice_answers_json: {json.dumps(choice_answers_json or '')}
- request_spec_constraints_json: {json.dumps(request_spec_constraints_json or '')}

Schema:
{{
  "product_category": "string (concise slug, e.g. 'running_shoes')",
  "taxonomy_version": "string|null",
  "category_path": ["array", "of", "strings"],
  "product_name": "string|null",
  "brand": "string|null",
  "model": "string|null",
  "min_price": "number|null",
  "max_price": "number|null",
  "price_flexibility": "'strict'|'flexible'|'unknown'|null",
  "condition": "'new'|'used'|'refurbished'|null",
  "features": {{"key": "value pairs"}},
  "keywords": ["short", "lowercase", "tokens"],
  "exclude_keywords": [],
  "confidence": 0.0-1.0,
  "raw_input": "string"
}}

Rules:
- product_category is required and should be a concise slug (e.g. "running_shoes").
- min_price/max_price should be numbers if present.
- features should include non-price constraints.
- keywords should be short, lower-case tokens.
- confidence should be 0-1.
"""

    text = await call_gemini(prompt, timeout=15.0)
    return _extract_json(text)


async def extract_search_intent(
    display_query: str,
    row_title: Optional[str] = None,
    project_title: Optional[str] = None,
    choice_answers_json: Optional[str] = None,
    request_spec_constraints_json: Optional[str] = None,
) -> SearchIntentResult:
    """
    Extract structured search intent — tries LLM first, falls back to heuristic.
    Ported from BFF's extractSearchIntent() in intent/index.ts.
    """
    if not _get_gemini_api_key():
        return build_heuristic_intent(display_query, row_title, choice_answers_json, request_spec_constraints_json)

    try:
        parsed = await _extract_intent_with_llm(
            display_query, row_title, project_title,
            choice_answers_json, request_spec_constraints_json,
        )
        return SearchIntentResult(
            product_category=parsed.get("product_category", "unknown"),
            taxonomy_version=parsed.get("taxonomy_version"),
            category_path=parsed.get("category_path", []),
            product_name=parsed.get("product_name"),
            brand=parsed.get("brand"),
            model=parsed.get("model"),
            min_price=parsed.get("min_price"),
            max_price=parsed.get("max_price"),
            price_flexibility=parsed.get("price_flexibility"),
            condition=parsed.get("condition"),
            features=parsed.get("features", {}),
            keywords=parsed.get("keywords", []),
            exclude_keywords=parsed.get("exclude_keywords", []),
            confidence=parsed.get("confidence", 0.5),
            raw_input=parsed.get("raw_input", display_query or ""),
            source="llm",
        )
    except Exception as e:
        fallback = build_heuristic_intent(display_query, row_title, choice_answers_json, request_spec_constraints_json)
        fallback.error = str(e)
        return fallback
