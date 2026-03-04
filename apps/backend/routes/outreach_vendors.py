"""
Vendor directory search, detail, checklist, and template endpoints.

Extracted from routes/outreach.py to keep files under 450 lines.
These are read-only vendor lookup endpoints used by the frontend.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from models import VendorProfile
from database import get_session
from services.vendors import search_checklist, get_checklist_summary, get_email_template

router = APIRouter(prefix="/outreach", tags=["outreach-vendors"])


@router.get("/vendors/search")
async def search_vendors_endpoint(
    q: str = "",
    category: Optional[str] = None,
    limit: int = 10,
    session=Depends(get_session),
):
    """
    Full-text search across vendor directory (VendorProfile table).
    Searches company, description, specialties, and profile_text via ILIKE.
    """
    from sqlalchemy import or_

    stmt = select(VendorProfile)
    if category:
        stmt = stmt.where(VendorProfile.category == category.lower().strip())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                VendorProfile.name.ilike(pattern),
                VendorProfile.description.ilike(pattern),
                VendorProfile.specialties.ilike(pattern),
                VendorProfile.profile_text.ilike(pattern),
                VendorProfile.tagline.ilike(pattern),
            )
        )
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    profiles = result.scalars().all()

    vendors = []
    for vp in profiles:
        vendors.append({
            "title": vp.name,
            "description": vp.tagline or vp.description,
            "price": None,
            "url": vp.website or (f"mailto:{vp.email}" if vp.email else None),
            "image_url": vp.image_url,
            "source": "directory",
            "is_service_provider": True,
            "vendor_company": vp.name,
            "vendor_email": vp.email,
            "category": vp.category,
            "website": vp.website,
        })
    return {
        "query": q,
        "category": category,
        "total": len(vendors),
        "vendors": vendors,
    }


@router.get("/vendors/detail/{company_name}")
async def get_vendor_detail_endpoint(
    company_name: str,
    session=Depends(get_session),
):
    """Get full detail for a specific vendor by company name (partial match)."""
    result = await session.execute(
        select(VendorProfile).where(
            VendorProfile.name.ilike(f"%{company_name}%")
        )
    )
    vp = result.scalar_one_or_none()
    if not vp:
        raise HTTPException(status_code=404, detail=f"Vendor not found: {company_name}")
    return {
        "id": vp.id,
        "company": vp.name,
        "category": vp.category,
        "website": vp.website,
        "contact_email": vp.email,
        "contact_phone": vp.phone,
        "specialties": vp.specialties,
        "description": vp.description,
        "tagline": vp.tagline,
        "image_url": vp.image_url,
        "vendor_id": vp.id,
        "created_at": vp.created_at.isoformat() if vp.created_at else None,
    }


@router.get("/checklist")
async def get_checklist_endpoint(q: str = "", must_have_only: bool = False):
    """Get or search the charter due-diligence checklist."""
    if q:
        items = search_checklist(q, must_have_only=must_have_only)
        return {"query": q, "must_have_only": must_have_only, "total": len(items), "items": items}

    summary = get_checklist_summary()
    if must_have_only:
        items = search_checklist("", must_have_only=True)
        return {"must_have_only": True, "total": len(items), "items": items, "summary": summary}

    items = search_checklist("")
    return {"total": len(items), "items": items, "summary": summary}


@router.get("/email-template")
async def get_email_template_endpoint():
    """Get the RFP email template for charter quote requests."""
    return get_email_template()
