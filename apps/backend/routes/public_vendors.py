"""
Public vendor directory endpoints — no auth required.

Provides paginated vendor listing, vector search, and individual vendor detail.
Never exposes email or phone — only public business information.
"""

import hashlib
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

    return {
        "id": v.id,
        "slug": slug,
        "name": v.name,
        "tagline": v.tagline,
        "description": v.description,
        "category": v.category,
        "specialties": v.specialties,
        "service_areas": v.service_areas,
        "website": v.website,
        "image_url": v.image_url,
        "is_verified": v.is_verified,
        "tier_affinity": v.tier_affinity,
    }


class VendorListResponse(BaseModel):
    vendors: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


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

        # Map SearchResults back to vendor detail
        vendor_ids = []
        for r in results:
            if r.raw_data and r.raw_data.get("vendor_id"):
                vendor_ids.append(r.raw_data["vendor_id"])

        if vendor_ids:
            stmt = select(Vendor).where(Vendor.id.in_(vendor_ids))
            db_result = await session.exec(stmt)
            vendor_map = {v.id: v for v in db_result.all()}
            vendors_out = []
            for vid in vendor_ids:
                if vid in vendor_map:
                    vendors_out.append(_vendor_to_public(vendor_map[vid]))
            return {"vendors": vendors_out, "query": q, "count": len(vendors_out)}

        # Fallback: return search results directly
        return {
            "vendors": [
                {
                    "name": r.title,
                    "description": r.raw_data.get("description") if r.raw_data else None,
                    "website": r.raw_data.get("website") if r.raw_data else None,
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

    # Prefer canonical slug column
    stmt = select(Vendor).where(Vendor.slug == vendor_slug)
    result = await session.exec(stmt)
    vendor = result.first()

    # Fallback: handle name-id slugs like "wimco-6135"
    if not vendor:
        m = re.search(r"-(\d+)$", vendor_slug)
        if m:
            try:
                vendor_id = int(m.group(1))
                vendor = await session.get(Vendor, vendor_id)
            except Exception:
                vendor = None

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    out = _vendor_to_public(vendor)
    out["seo_content"] = vendor.seo_content
    out["schema_markup"] = vendor.schema_markup
    return out
