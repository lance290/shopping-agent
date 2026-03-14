"""Bid persistence logic extracted from SourcingService."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row, Seller
from sourcing.discovery.gating import visibility_threshold as discovery_visibility_threshold
from sourcing.models import NormalizedResult

logger = logging.getLogger(__name__)


def safe_total_cost(price: Optional[float], shipping: Optional[float]) -> Optional[float]:
    """Compute total_cost without crashing on None values."""
    if price is None:
        return None
    return (price or 0.0) + (shipping or 0.0)


def build_enriched_provenance(res: NormalizedResult, row: Optional["Row"]) -> dict:
    from sourcing.provenance import build_enriched_provenance as _build
    return _build(res, row)


def filter_discovery_results_for_bid_persistence(row: Row, results: List[NormalizedResult]) -> List[NormalizedResult]:
    high_risk = (row.desire_tier or "").strip().lower() in {"high_value", "advisory"} or (row.service_category or "").strip().lower() in {
        "private_aviation",
        "yacht_charter",
        "real_estate",
    }
    persisted: List[NormalizedResult] = []
    for result in results:
        raw_data = result.raw_data if isinstance(result.raw_data, dict) else {}
        provenance = result.provenance if isinstance(result.provenance, dict) else {}
        score = provenance.get("score", {}) if isinstance(provenance.get("score"), dict) else {}
        if raw_data.get("admissibility_status") != "admitted":
            continue
        min_score = max(discovery_visibility_threshold(), 0.7 if high_risk else 0.0)
        if float(score.get("combined") or 0.0) < min_score:
            continue
        candidate_type = str(raw_data.get("candidate_type") or provenance.get("candidate_type") or "").strip()
        if high_risk and candidate_type in {"directory_or_aggregator", "listing_or_inventory_page", "editorial_or_irrelevant"}:
            continue
        if not (provenance.get("official_site") or raw_data.get("official_site")):
            continue
        if not result.merchant_domain:
            continue
        if high_risk and not (
            raw_data.get("first_party_contact")
            or provenance.get("first_party_contact")
            or raw_data.get("email")
            or raw_data.get("phone")
            or candidate_type in {"brokerage_or_agent_site", "marketplace_or_exchange", "brand_site", "official_vendor_site"}
        ):
            continue
        if not (raw_data.get("email") or raw_data.get("phone") or result.url):
            continue
        persisted.append(result)
    return persisted


async def get_or_create_seller(
    session: AsyncSession,
    name: str,
    domain: str,
    contact_data: Optional[Dict[str, Any]] = None,
) -> Seller:
    stmt = (
        select(Seller)
        .where(Seller.name == name)
    )
    result = await session.exec(stmt)
    seller = result.first()

    if not seller:
        seller = Seller(name=name, domain=domain)
        session.add(seller)

    # Enrich vendor record with contact data from Apify/web results
    # (only fill empty fields — never overwrite existing data)
    if contact_data and isinstance(contact_data, dict):
        if not seller.phone and contact_data.get("phone"):
            seller.phone = contact_data["phone"]
        if not seller.email and contact_data.get("email"):
            seller.email = contact_data["email"]
        if not seller.website and contact_data.get("website"):
            seller.website = contact_data["website"]
        if not seller.store_geo_location and contact_data.get("location_hint"):
            seller.store_geo_location = contact_data["location_hint"]
        if not seller.description and contact_data.get("description"):
            seller.description = contact_data["description"]
        if not seller.source_provenance and contact_data.get("source_provenance"):
            seller.source_provenance = contact_data["source_provenance"]

    await session.flush()  # Get ID without committing — avoids partial commits mid-loop

    return seller


async def persist_results(
    session: AsyncSession,
    row_id: int,
    results: List[NormalizedResult],
    row: Optional["Row"] = None,
) -> List[Bid]:
    """Persist normalized results as Bids, creating Sellers as needed. Returns list of Bids."""
    if not results:
        return []

    # Pre-resolve all sellers in a single pass to avoid mid-loop commits
    seller_cache: dict[str, Seller] = {}
    unique_merchants = {
        (r.merchant_name, r.merchant_domain)
        for r in results
        if not str(r.source or "").startswith("vendor_discovery_")
    }
    # Build contact data lookup keyed by merchant name for vendor enrichment
    contact_data_by_merchant: dict[str, Dict[str, Any]] = {}
    for r in results:
        if r.merchant_name and isinstance(r.raw_data, dict) and r.raw_data:
            cd = dict(r.raw_data)
            # Tag source provenance based on result source
            if r.source.startswith("apify_"):
                cd.setdefault("source_provenance", "google_maps")
            elif r.source.startswith("web_"):
                cd.setdefault("source_provenance", "web_search")
            contact_data_by_merchant[r.merchant_name] = cd

    for name, domain in unique_merchants:
        seller_cache[name] = await get_or_create_seller(
            session, name, domain, contact_data=contact_data_by_merchant.get(name),
        )

    # Fetch existing bids to handle upserts (deduplication)
    existing_bids_stmt = select(Bid).where(Bid.row_id == row_id)
    existing_bids_res = await session.exec(existing_bids_stmt)
    existing_bids = existing_bids_res.all()
    
    bids_by_canonical = {b.canonical_url: b for b in existing_bids if b.canonical_url}
    bids_by_url = {b.item_url: b for b in existing_bids if b.item_url}

    new_bids_count = 0
    updated_bids_count = 0

    for res in results:
        seller = seller_cache.get(res.merchant_name)
        
        existing_bid = None
        if res.canonical_url and res.canonical_url in bids_by_canonical:
            existing_bid = bids_by_canonical[res.canonical_url]
        elif res.url in bids_by_url:
            existing_bid = bids_by_url[res.url]

        provenance_json = build_enriched_provenance(res, row)

        score_data = res.provenance.get("score", {}) if res.provenance else {}
        combined_score = score_data.get("combined")
        price_score_val = score_data.get("price")
        relevance_score_val = score_data.get("relevance")
        quality_score_val = score_data.get("quality")
        diversity_bonus_val = score_data.get("diversity")

        # Mark as service provider if the row is a service search or
        # the result came from Google Places (always a real business)
        is_svc = bool(
            (row and row.is_service)
            or res.source.startswith("apify_compass")
            or res.source == "vendor_directory"
        )

        source_tier = "marketplace"
        if res.source in ("seller_quote", "vendor_directory"):
            source_tier = "outreach"
        elif is_svc and res.source.startswith("apify_"):
            source_tier = "outreach"
        elif res.source == "registered_merchant":
            source_tier = "registered"

        if existing_bid:
            existing_bid.price = res.price if res.price is not None else existing_bid.price
            existing_bid.total_cost = safe_total_cost(existing_bid.price, existing_bid.shipping_cost)
            existing_bid.currency = res.currency
            existing_bid.item_title = res.title
            existing_bid.image_url = res.image_url
            existing_bid.source = res.source
            existing_bid.vendor_id = seller.id if seller else existing_bid.vendor_id
            existing_bid.canonical_url = res.canonical_url
            existing_bid.provenance = provenance_json
            existing_bid.combined_score = combined_score
            existing_bid.price_score = price_score_val
            existing_bid.relevance_score = relevance_score_val
            existing_bid.quality_score = quality_score_val
            existing_bid.diversity_bonus = diversity_bonus_val
            existing_bid.source_tier = source_tier
            existing_bid.is_service_provider = is_svc or existing_bid.is_service_provider
            existing_bid.is_superseded = False
            existing_bid.superseded_at = None
            if isinstance(res.raw_data, dict):
                existing_bid.contact_email = res.raw_data.get("email") or existing_bid.contact_email
                existing_bid.contact_phone = res.raw_data.get("phone") or existing_bid.contact_phone
                existing_bid.contact_name = res.merchant_name or existing_bid.contact_name
            
            session.add(existing_bid)
            updated_bids_count += 1
        else:
            new_bid = Bid(
                row_id=row_id,
                vendor_id=seller.id if seller else None,
                price=res.price,
                total_cost=safe_total_cost(res.price, 0.0),
                currency=res.currency,
                item_title=res.title,
                item_url=res.url,
                image_url=res.image_url,
                source=res.source,
                canonical_url=res.canonical_url,
                is_selected=False,
                is_service_provider=is_svc,
                provenance=provenance_json,
                combined_score=combined_score,
                price_score=price_score_val,
                relevance_score=relevance_score_val,
                quality_score=quality_score_val,
                diversity_bonus=diversity_bonus_val,
                source_tier=source_tier,
                contact_name=res.merchant_name,
                contact_email=res.raw_data.get("email") if isinstance(res.raw_data, dict) else None,
                contact_phone=res.raw_data.get("phone") if isinstance(res.raw_data, dict) else None,
            )
            session.add(new_bid)
            if new_bid.canonical_url:
                bids_by_canonical[new_bid.canonical_url] = new_bid
            if new_bid.item_url:
                bids_by_url[new_bid.item_url] = new_bid
            
            new_bids_count += 1

    await session.commit()
    
    # Authoritative reload: query ALL bids for this row from DB.
    # Never rely on in-memory object IDs which may be expired after async commit.
    stmt = (
        select(Bid)
        .where(Bid.row_id == row_id, Bid.is_superseded == False)
        .options(selectinload(Bid.seller))
        .order_by(Bid.combined_score.desc().nullslast(), Bid.id)
    )
    result = await session.exec(stmt)
    all_bids = list(result.all())
        
    logger.info(f"[SourcingService] Row {row_id}: Created {new_bids_count}, Updated {updated_bids_count}, Total {len(all_bids)} bids")
    return all_bids
