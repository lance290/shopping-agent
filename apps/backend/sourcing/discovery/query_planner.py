"""Build request-shaped query variants for live vendor discovery."""

from __future__ import annotations

from typing import List

from sourcing.models import SearchIntent


def build_discovery_queries(intent: SearchIntent, mode: str) -> List[str]:
    base = (intent.product_name or intent.raw_input or "").strip()
    if not base:
        base = intent.product_category.replace("_", " ")

    queries = [base]
    targets = intent.location_context.targets.non_empty_items()
    location_bits = [value for value in targets.values() if value]
    location_suffix = " ".join(location_bits[:2]).strip()
    
    strategies = set(intent.search_strategies) if intent.search_strategies else set()

    if mode == "luxury_brokerage_discovery":
        queries.extend([
            f"{location_suffix} luxury real estate agent".strip(),
            f"{location_suffix} boutique luxury real estate brokerage".strip(),
            f"{location_suffix} estate listing specialist".strip(),
        ])
    elif mode == "asset_market_discovery":
        queries.extend([
            f"{base} broker".strip(),
            f"{base} dealer".strip(),
            f"{location_suffix} {base} broker".strip(),
        ])
    elif mode == "uhnw_goods_discovery":
        queries.extend([
            f"{base} luxury dealer".strip(),
            f"{base} auction house".strip(),
            f"{base} authorized dealer".strip(),
        ])
    else:
        queries.extend([
            f"{location_suffix} {base}".strip(),
            f"{location_suffix} {base} official site".strip(),
            f"{location_suffix} {base} specialist".strip(),
        ])

    # Add strategy-driven queries
    if "local_network_first" in strategies and location_suffix:
        queries.append(f"{location_suffix} local {base} specialists".strip())
    if "prestige_first" in strategies:
        queries.append(f"high end {base}".strip())
        queries.append(f"luxury {base}".strip())
    if "official_first" in strategies:
        queries.append(f"{base} official authorized".strip())
    if "market_first" in strategies:
        queries.append(f"{base} marketplace".strip())

    seen = set()
    ordered: List[str] = []
    for query in queries:
        cleaned = " ".join(query.split()).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered[:6]
