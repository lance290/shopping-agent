"""Vendor endorsement endpoints — authenticated EA curation workflows.

Allows authenticated users to:
- Endorse/rate a vendor (create or update)
- List their endorsements
- Delete an endorsement
- Edit vendor contact/category fields (admin or endorser)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models.auth import AuthSession, AuditLog, User
from models.bids import Vendor, VendorEndorsement

logger = logging.getLogger(__name__)
router = APIRouter(tags=["vendor-endorsements"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class EndorsementCreate(BaseModel):
    vendor_id: int
    trust_rating: Optional[int] = Field(None, ge=1, le=5)
    recommended_for_categories: Optional[List[str]] = None
    recommended_for_regions: Optional[List[str]] = None
    notes: Optional[str] = None
    is_personal_contact: bool = False


class EndorsementUpdate(BaseModel):
    trust_rating: Optional[int] = Field(None, ge=1, le=5)
    recommended_for_categories: Optional[List[str]] = None
    recommended_for_regions: Optional[List[str]] = None
    notes: Optional[str] = None
    is_personal_contact: Optional[bool] = None


class VendorFieldUpdate(BaseModel):
    """Allowed fields for EA vendor editing."""
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    contact_form_url: Optional[str] = None
    booking_url: Optional[str] = None
    category: Optional[str] = None
    secondary_categories: Optional[List[str]] = None
    service_regions: Optional[List[str]] = None
    store_geo_location: Optional[str] = None
    vendor_type: Optional[str] = None
    description: Optional[str] = None


def _endorsement_to_dict(e: VendorEndorsement) -> Dict[str, Any]:
    return {
        "id": e.id,
        "vendor_id": e.vendor_id,
        "user_id": e.user_id,
        "trust_rating": e.trust_rating,
        "recommended_for_categories": e.recommended_for_categories,
        "recommended_for_regions": e.recommended_for_regions,
        "notes": e.notes,
        "is_personal_contact": e.is_personal_contact,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_user(
    authorization: Optional[str],
    session: AsyncSession,
) -> AuthSession:
    auth = await get_current_session(authorization, session)
    if not auth or not auth.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth


async def _audit(
    session: AsyncSession,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Any,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=json.dumps(details, default=str) if details else None,
    )
    session.add(log)


# ---------------------------------------------------------------------------
# Endorsement CRUD
# ---------------------------------------------------------------------------

@router.post("/api/vendors/{vendor_id}/endorsements")
async def create_or_update_endorsement(
    vendor_id: int,
    body: EndorsementCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Create or update the current user's endorsement for a vendor."""
    auth = await _require_user(authorization, session)

    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Upsert: one endorsement per user per vendor
    stmt = select(VendorEndorsement).where(
        VendorEndorsement.vendor_id == vendor_id,
        VendorEndorsement.user_id == auth.user_id,
    )
    result = await session.exec(stmt)
    existing = result.first()

    if existing:
        if body.trust_rating is not None:
            existing.trust_rating = body.trust_rating
        if body.recommended_for_categories is not None:
            existing.recommended_for_categories = body.recommended_for_categories
        if body.recommended_for_regions is not None:
            existing.recommended_for_regions = body.recommended_for_regions
        if body.notes is not None:
            existing.notes = body.notes
        existing.is_personal_contact = body.is_personal_contact
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        await _audit(session, auth.user_id, "vendor_endorsement.update", "vendor_endorsement", existing.id, {
            "vendor_id": vendor_id, "trust_rating": body.trust_rating,
        })
        await session.commit()
        await session.refresh(existing)
        return _endorsement_to_dict(existing)

    endorsement = VendorEndorsement(
        vendor_id=vendor_id,
        user_id=auth.user_id,
        trust_rating=body.trust_rating,
        recommended_for_categories=body.recommended_for_categories,
        recommended_for_regions=body.recommended_for_regions,
        notes=body.notes,
        is_personal_contact=body.is_personal_contact,
    )
    session.add(endorsement)
    await _audit(session, auth.user_id, "vendor_endorsement.create", "vendor_endorsement", vendor_id, {
        "vendor_id": vendor_id, "trust_rating": body.trust_rating,
    })
    await session.commit()
    await session.refresh(endorsement)
    return _endorsement_to_dict(endorsement)


@router.get("/api/vendors/{vendor_id}/endorsements")
async def list_endorsements_for_vendor(
    vendor_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth = await _require_user(authorization, session)
    stmt = select(VendorEndorsement).where(
        VendorEndorsement.vendor_id == vendor_id,
        VendorEndorsement.user_id == auth.user_id,
    )
    result = await session.exec(stmt)
    endorsements = result.all()
    return {"endorsements": [_endorsement_to_dict(e) for e in endorsements]}


@router.get("/api/me/endorsements")
async def list_my_endorsements(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """List the current user's endorsements."""
    auth = await _require_user(authorization, session)
    stmt = select(VendorEndorsement).where(VendorEndorsement.user_id == auth.user_id)
    result = await session.exec(stmt)
    endorsements = result.all()
    return {"endorsements": [_endorsement_to_dict(e) for e in endorsements]}


@router.delete("/api/vendors/{vendor_id}/endorsements")
async def delete_endorsement(
    vendor_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Delete the current user's endorsement for a vendor."""
    auth = await _require_user(authorization, session)
    stmt = select(VendorEndorsement).where(
        VendorEndorsement.vendor_id == vendor_id,
        VendorEndorsement.user_id == auth.user_id,
    )
    result = await session.exec(stmt)
    existing = result.first()
    if not existing:
        raise HTTPException(status_code=404, detail="Endorsement not found")

    await _audit(session, auth.user_id, "vendor_endorsement.delete", "vendor_endorsement", existing.id, {
        "vendor_id": vendor_id,
    })
    await session.delete(existing)
    await session.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Vendor field editing (authenticated)
# ---------------------------------------------------------------------------

@router.patch("/api/vendors/{vendor_id}")
async def update_vendor_fields(
    vendor_id: int,
    body: VendorFieldUpdate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth = await _require_user(authorization, session)
    user = await session.get(User, auth.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if not user.is_admin:
        endorsement_stmt = select(VendorEndorsement).where(
            VendorEndorsement.vendor_id == vendor_id,
            VendorEndorsement.user_id == auth.user_id,
        )
        endorsement_result = await session.exec(endorsement_stmt)
        endorsement = endorsement_result.first()
        if not endorsement:
            raise HTTPException(status_code=403, detail="Only endorsers or admins can edit this vendor")

    changes: Dict[str, Dict[str, Any]] = {}
    update_data = body.model_dump(exclude_unset=True)

    for field_name, new_value in update_data.items():
        old_value = getattr(vendor, field_name, None)
        if old_value != new_value:
            changes[field_name] = {"old": old_value, "new": new_value}
            setattr(vendor, field_name, new_value)

    if not changes:
        return {"status": "no_changes", "vendor_id": vendor_id}

    vendor.updated_at = datetime.utcnow()
    session.add(vendor)

    await _audit(session, auth.user_id, "vendor.update", "vendor", vendor_id, changes)
    await session.commit()
    await session.refresh(vendor)

    return {
        "status": "updated",
        "vendor_id": vendor_id,
        "changes": {k: v["new"] for k, v in changes.items()},
    }
