"""Provenance enrichment helpers — extracted from sourcing/service.py."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def build_enriched_provenance(res, row: Optional[object]) -> dict:
    """Merge normalizer provenance with search intent context, choice factors, and chat excerpts."""
    provenance = dict(res.provenance) if res.provenance else {}

    # Ensure product_info exists
    product_info = provenance.get("product_info", {})
    if not isinstance(product_info, dict):
        product_info = {}
    if res.source and not product_info.get("source_provider"):
        product_info["source_provider"] = res.source
    provenance["product_info"] = product_info

    # Enrich matched_features from search intent
    matched_features = list(provenance.get("matched_features", []))
    if row and getattr(row, "search_intent", None):
        try:
            intent = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(intent, dict):
                keywords = intent.get("keywords", [])
                if keywords:
                    matched_features.append(f"Matches: {', '.join(keywords[:5])}")
                brand = intent.get("brand")
                if brand:
                    if not product_info.get("brand"):
                        product_info["brand"] = brand
                        provenance["product_info"] = product_info
                features = intent.get("features", {})
                if features:
                    for key, val in list(features.items())[:3]:
                        label = f"{key}: {val}" if not isinstance(val, list) else f"{key}: {', '.join(val)}"
                        matched_features.append(label)
        except (json.JSONDecodeError, TypeError):
            pass

    # Match against choice_answers for concrete "why this matches" signals
    if row and getattr(row, "choice_answers", None):
        try:
            answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
            if isinstance(answers, dict):
                price = res.price

                # Budget check
                budget = answers.get("max_price") or answers.get("max_budget") or answers.get("budget")
                if budget and price and price > 0:
                    try:
                        budget_val = float(budget)
                        if price <= budget_val:
                            matched_features.append(f"Price ${price:.2f} is within your ${budget_val:.0f} budget")
                    except (ValueError, TypeError):
                        pass

                # Brand check
                pref_brand = answers.get("preferred_brand") or answers.get("brand")
                product_brand = product_info.get("brand") or ""
                if pref_brand and product_brand and str(pref_brand).lower() in str(product_brand).lower():
                    matched_features.append(f"Brand: {product_brand} (matches your preference)")

                # Condition check
                pref_condition = answers.get("condition")
                product_condition = product_info.get("condition", "new")
                if pref_condition and product_condition and str(pref_condition).lower() == str(product_condition).lower():
                    matched_features.append(f"Condition: {product_condition} (as requested)")

                # Rating check
                if hasattr(res, "rating") and res.rating and float(res.rating) >= 4.0:
                    matched_features.append(f"Highly rated: {res.rating}/5 stars")

                # Free shipping check
                if hasattr(res, "shipping_info") and res.shipping_info:
                    shipping_str = str(res.shipping_info).lower()
                    if "free" in shipping_str:
                        matched_features.append("Free shipping available")
        except (json.JSONDecodeError, TypeError):
            pass

    # Deduplicate matched features
    seen = set()
    unique_features = []
    for f in matched_features:
        if f not in seen:
            seen.add(f)
            unique_features.append(f)
    provenance["matched_features"] = unique_features

    # Extract chat excerpts from row
    if row and getattr(row, "chat_history", None) and not provenance.get("chat_excerpts"):
        try:
            chat = json.loads(row.chat_history) if isinstance(row.chat_history, str) else row.chat_history
            if isinstance(chat, list):
                excerpts = []
                for msg in chat:
                    if not isinstance(msg, dict):
                        continue
                    role = msg.get("role", "")
                    content = str(msg.get("content", ""))
                    if role in ("user", "assistant") and len(content) > 10:
                        excerpts.append({"role": role, "content": content[:200]})
                        if len(excerpts) >= 3:
                            break
                if excerpts:
                    provenance["chat_excerpts"] = excerpts
        except (json.JSONDecodeError, TypeError):
            pass

    return provenance
