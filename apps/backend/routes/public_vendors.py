"""
Public vendor directory endpoints — no auth required.

Provides paginated vendor listing, vector search, and individual vendor detail.
Never exposes email or phone — only public business information.
"""

import hashlib
import json
import logging
import os
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from fastapi import Depends
from models.bids import Vendor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["public-vendors"])

# Rate limiting
_rate_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 60


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    hits = _rate_store[ip]
    _rate_store[ip] = [t for t in hits if t > now - RATE_WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


def _vendor_to_public(v: Vendor) -> Dict[str, Any]:
    """Convert vendor to public-safe dict — NEVER expose email or phone."""
    slug = v.slug
    if not slug:
        slug = (v.name or "").lower().strip()
        for ch in [" ", "'", '"', "&", "/", "\\", ".", ","]:
            slug = slug.replace(ch, "-")
        slug = "-".join(part for part in slug.split("-") if part)
        slug = f"{slug}-{v.id}" if slug else f"vendor-{v.id}"

    def _parse_json_field(val: Any) -> Any:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, ValueError):
                return None
        return val

    return {
        "id": v.id,
        "slug": slug,
        "name": v.name,
        "tagline": v.tagline,
        "description": v.description,
        "category": v.category,
        "store_geo_location": v.store_geo_location,
        "specialties": v.specialties,
        "website": v.website,
        "image_url": v.image_url,
        "is_verified": v.is_verified,
        "tier_affinity": v.tier_affinity,
        "seo_content": _parse_json_field(v.seo_content),
        "schema_markup": _parse_json_field(v.schema_markup),
    }


class VendorListResponse(BaseModel):
    vendors: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


@router.get("/api/public/vendors/filter", response_model=VendorListResponse)
async def filter_vendors(
    request: Request,
    city: str = Query(..., min_length=1, max_length=100),
    category: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    offset = (page - 1) * page_size
    city_like = f"%{city}%"
    cat_like = f"%{category}%"

    base_where = (
        Vendor.embedding.isnot(None),
        Vendor.website.isnot(None),
        Vendor.store_geo_location.isnot(None),
        Vendor.store_geo_location.ilike(city_like),  # type: ignore
        Vendor.category.isnot(None),
        Vendor.category.ilike(cat_like),  # type: ignore
    )

    count_stmt = select(func.count(col(Vendor.id))).where(*base_where)
    count_result = await session.exec(count_stmt)
    total = count_result.one()

    stmt = (
        select(Vendor)
        .where(*base_where)
        .order_by(Vendor.name)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.exec(stmt)
    vendors = result.all()

    return VendorListResponse(
        vendors=[_vendor_to_public(v) for v in vendors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/public/vendors", response_model=VendorListResponse)
async def list_vendors(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Paginated vendor listing — only vendors with embeddings and websites."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    offset = (page - 1) * page_size

    # Count total
    count_stmt = select(func.count(col(Vendor.id))).where(
        Vendor.embedding.isnot(None),
        Vendor.website.isnot(None),
    )
    count_result = await session.exec(count_stmt)
    total = count_result.one()

    # Fetch page
    stmt = (
        select(Vendor)
        .where(
            Vendor.embedding.isnot(None),
            Vendor.website.isnot(None),
        )
        .order_by(Vendor.name)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.exec(stmt)
    vendors = result.all()

    return VendorListResponse(
        vendors=[_vendor_to_public(v) for v in vendors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/public/vendors/search")
async def search_vendors(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Vector search vendors by natural language query."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    logger.info(f"[PublicVendors] Search: {q!r}")

    # Use VendorDirectoryProvider for vector search
    try:
        from sourcing.vendor_provider import VendorDirectoryProvider
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        provider = VendorDirectoryProvider(db_url)
        results = await provider.search(q)

        # Map SearchResults back to vendor detail via merchant name
        vendor_names = [r.merchant for r in results if r.merchant]
        if vendor_names:
            stmt = select(Vendor).where(Vendor.name.in_(vendor_names))
            db_result = await session.exec(stmt)
            vendor_map = {v.name: v for v in db_result.all()}
            vendors_out = []
            seen = set()
            for r in results[:limit]:
                v = vendor_map.get(r.merchant)
                if v and v.id not in seen:
                    seen.add(v.id)
                    vendors_out.append(_vendor_to_public(v))
            return {"vendors": vendors_out, "query": q, "count": len(vendors_out)}

        # Fallback: return search results directly (no DB match)
        return {
            "vendors": [
                {
                    "name": r.title,
                    "description": r.shipping_info,
                    "website": r.url,
                    "image_url": r.image_url,
                    "source": r.source,
                }
                for r in results[:limit]
            ],
            "query": q,
            "count": len(results[:limit]),
        }
    except Exception as e:
        logger.error(f"[PublicVendors] Vector search failed: {e}")
        # Fallback to ILIKE search
        stmt = (
            select(Vendor)
            .where(
                Vendor.embedding.isnot(None),
                Vendor.website.isnot(None),
                (Vendor.name.ilike(f"%{q}%")) | (Vendor.description.ilike(f"%{q}%"))  # type: ignore
            )
            .limit(limit)
        )
        result = await session.exec(stmt)
        vendors = result.all()
        return {
            "vendors": [_vendor_to_public(v) for v in vendors],
            "query": q,
            "count": len(vendors),
        }


@router.get("/api/public/vendors/facets")
async def list_vendor_facets(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Return distinct (city, category) pairs for sitemap and internal linking.

    Parses store_geo_location (comma-separated city list) and returns
    de-duped {cities: [...], categories: [...], combos: [{city, category}, ...]}.
    Capped at 500 combos to keep responses reasonable.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    stmt = (
        select(Vendor.store_geo_location, Vendor.category)
        .where(
            Vendor.embedding.isnot(None),
            Vendor.website.isnot(None),
            Vendor.store_geo_location.isnot(None),
            Vendor.category.isnot(None),
        )
        .distinct()
    )
    result = await session.exec(stmt)
    rows = result.all()

    cities_set: set = set()
    categories_set: set = set()
    combos: List[Dict[str, str]] = []

    for geo, cat in rows:
        if not geo or not cat:
            continue
        cat_clean = cat.strip()
        if not cat_clean:
            continue
        categories_set.add(cat_clean)
        for part in geo.split(","):
            city = part.strip()
            if not city or len(city) < 2:
                continue
            cities_set.add(city)
            if len(combos) < 500:
                combos.append({"city": city, "category": cat_clean})

    return {
        "cities": sorted(cities_set),
        "categories": sorted(categories_set),
        "combos": combos,
    }


@router.get("/api/public/vendors/{vendor_id}")
async def get_vendor_detail(
    vendor_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Single vendor detail — public info only, no email/phone."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return _vendor_to_public(vendor)


def _compute_slug(name: str, vendor_id: int) -> str:
    """Generate a URL-safe slug from a vendor name + id (matches _vendor_to_public logic)."""
    slug = (name or "").lower().strip()
    for ch in [" ", "'", '"', "&", "/", "\\", ".", ","]:
        slug = slug.replace(ch, "-")
    slug = "-".join(part for part in slug.split("-") if part)
    return f"{slug}-{vendor_id}" if slug else f"vendor-{vendor_id}"


@router.get("/api/public/vendors/slug/{vendor_slug}")
async def get_vendor_detail_by_slug(
    vendor_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    vendor: Optional[Vendor] = None

    # 1. Prefer canonical slug column
    stmt = select(Vendor).where(Vendor.slug == vendor_slug)
    result = await session.exec(stmt)
    vendor = result.first()

    # 2. Fallback: handle computed name-id slugs like "wimco-6135"
    if not vendor:
        m = re.search(r"-(\d+)$", vendor_slug)
        if m:
            try:
                vendor_id = int(m.group(1))
                candidate = await session.get(Vendor, vendor_id)
                # Verify the slug actually matches this vendor to avoid ID-guessing
                if candidate and _compute_slug(candidate.name, candidate.id) == vendor_slug:
                    vendor = candidate
            except Exception:
                vendor = None

    # 3. Persist the slug so future lookups hit the fast path
    if vendor and not vendor.slug:
        try:
            vendor.slug = _compute_slug(vendor.name, vendor.id)
            session.add(vendor)
            await session.commit()
            await session.refresh(vendor)
        except Exception:
            pass  # Non-fatal — slug will be persisted on next write

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return _vendor_to_public(vendor)
