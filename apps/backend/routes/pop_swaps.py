"""Pop swap admin routes: CRUD + CSV import for coupon/swap offers."""

import csv
import io
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.coupons import PopSwap, PopSwapClaim
from services.coupon_provider import get_coupon_provider

logger = logging.getLogger(__name__)
swaps_router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SwapCreate(BaseModel):
    category: str
    swap_product_name: str
    target_product: Optional[str] = None
    swap_product_image: Optional[str] = None
    swap_product_url: Optional[str] = None
    offer_type: str = "coupon"
    savings_cents: int = 0
    discount_percent: Optional[float] = None
    offer_description: Optional[str] = None
    terms: Optional[str] = None
    brand_name: Optional[str] = None
    brand_contact_email: Optional[str] = None
    provider: str = "manual"
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = None


class SwapUpdate(BaseModel):
    category: Optional[str] = None
    swap_product_name: Optional[str] = None
    target_product: Optional[str] = None
    offer_type: Optional[str] = None
    savings_cents: Optional[int] = None
    offer_description: Optional[str] = None
    brand_name: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = None


class SwapSearchRequest(BaseModel):
    category: str
    product_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------


@swaps_router.post("/admin/swaps")
async def create_swap(
    body: SwapCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new swap offer (admin only)."""
    swap = PopSwap(
        category=body.category.strip().lower(),
        swap_product_name=body.swap_product_name.strip(),
        target_product=body.target_product.strip() if body.target_product else None,
        swap_product_image=body.swap_product_image,
        swap_product_url=body.swap_product_url,
        offer_type=body.offer_type,
        savings_cents=body.savings_cents,
        discount_percent=body.discount_percent,
        offer_description=body.offer_description,
        terms=body.terms,
        brand_name=body.brand_name,
        brand_contact_email=body.brand_contact_email,
        provider=body.provider,
        expires_at=body.expires_at,
        max_redemptions=body.max_redemptions,
    )
    session.add(swap)
    await session.commit()
    await session.refresh(swap)
    logger.info(f"[PopSwap] Created swap #{swap.id}: {swap.swap_product_name} in {swap.category}")
    return {"id": swap.id, "swap_product_name": swap.swap_product_name, "category": swap.category}


@swaps_router.get("/admin/swaps")
async def list_swaps(
    active_only: bool = True,
    provider: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """List swap offers with optional filters."""
    stmt = select(PopSwap).order_by(PopSwap.created_at.desc()).limit(limit)

    if active_only:
        stmt = stmt.where(PopSwap.is_active == True)
    if provider:
        stmt = stmt.where(PopSwap.provider == provider)
    if category:
        stmt = stmt.where(PopSwap.category.ilike(f"%{category}%"))

    result = await session.exec(stmt)
    swaps = result.all()

    return {
        "count": len(swaps),
        "swaps": [
            {
                "id": s.id,
                "category": s.category,
                "target_product": s.target_product,
                "swap_product_name": s.swap_product_name,
                "offer_type": s.offer_type,
                "savings_cents": s.savings_cents,
                "savings_display": f"${s.savings_cents / 100:.2f}",
                "offer_description": s.offer_description,
                "brand_name": s.brand_name,
                "provider": s.provider,
                "is_active": s.is_active,
                "current_redemptions": s.current_redemptions,
                "max_redemptions": s.max_redemptions,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in swaps
        ],
    }


@swaps_router.patch("/admin/swaps/{swap_id}")
async def update_swap(
    swap_id: int,
    body: SwapUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an existing swap offer."""
    swap = await session.get(PopSwap, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "category" and value:
            value = value.strip().lower()
        setattr(swap, key, value)

    swap.updated_at = datetime.utcnow()
    session.add(swap)
    await session.commit()
    await session.refresh(swap)

    return {"id": swap.id, "updated": True}


@swaps_router.delete("/admin/swaps/{swap_id}")
async def deactivate_swap(
    swap_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Soft-deactivate a swap offer (set is_active=False)."""
    swap = await session.get(PopSwap, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Swap not found")

    swap.is_active = False
    swap.updated_at = datetime.utcnow()
    session.add(swap)
    await session.commit()
    return {"id": swap_id, "deactivated": True}


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------


@swaps_router.post("/admin/swaps/import-csv")
async def import_swaps_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Bulk import swap offers from a CSV file.

    Required columns: category, swap_product_name, savings_cents
    Optional columns: target_product, offer_type, offer_description,
                      brand_name, brand_contact_email, expires_at,
                      max_redemptions, swap_product_url, swap_product_image
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    errors: List[str] = []

    for i, row in enumerate(reader, start=2):  # row 2 = first data row
        try:
            category = (row.get("category") or "").strip().lower()
            swap_product_name = (row.get("swap_product_name") or "").strip()

            if not category or not swap_product_name:
                errors.append(f"Row {i}: missing category or swap_product_name")
                continue

            savings_str = row.get("savings_cents", "0")
            try:
                savings_cents = int(savings_str)
            except (ValueError, TypeError):
                errors.append(f"Row {i}: invalid savings_cents '{savings_str}'")
                continue

            expires_at = None
            if row.get("expires_at"):
                try:
                    expires_at = datetime.fromisoformat(row["expires_at"])
                except ValueError:
                    errors.append(f"Row {i}: invalid expires_at format")

            max_redemptions = None
            if row.get("max_redemptions"):
                try:
                    max_redemptions = int(row["max_redemptions"])
                except (ValueError, TypeError):
                    pass

            swap = PopSwap(
                category=category,
                swap_product_name=swap_product_name,
                target_product=(row.get("target_product") or "").strip() or None,
                offer_type=(row.get("offer_type") or "coupon").strip(),
                savings_cents=savings_cents,
                offer_description=(row.get("offer_description") or "").strip() or None,
                brand_name=(row.get("brand_name") or "").strip() or None,
                brand_contact_email=(row.get("brand_contact_email") or "").strip() or None,
                swap_product_url=(row.get("swap_product_url") or "").strip() or None,
                swap_product_image=(row.get("swap_product_image") or "").strip() or None,
                provider="manual",
                expires_at=expires_at,
                max_redemptions=max_redemptions,
            )
            session.add(swap)
            created += 1

        except Exception as e:
            errors.append(f"Row {i}: {e}")

    if created > 0:
        await session.commit()

    logger.info(f"[PopSwap] CSV import: {created} created, {len(errors)} errors")
    return {"created": created, "errors": errors}


# ---------------------------------------------------------------------------
# Search endpoint (uses CouponProvider abstraction)
# ---------------------------------------------------------------------------


@swaps_router.post("/swaps/search")
async def search_swaps(
    body: SwapSearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Search for available swap/coupon offers matching a category + product.
    Uses the AggregateProvider to query all active coupon sources.
    """
    provider = get_coupon_provider()
    offers = await provider.search_swaps(
        category=body.category.strip().lower(),
        product_name=body.product_name.strip() if body.product_name else None,
        session=session,
    )

    return {
        "category": body.category,
        "product_name": body.product_name,
        "offers": [o.to_dict() for o in offers],
        "count": len(offers),
    }
