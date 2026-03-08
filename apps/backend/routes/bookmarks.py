from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from database import get_session
from dependencies import get_current_session
from models import Vendor
from models.bookmarks import VendorBookmark
from pydantic import BaseModel

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

class VendorBookmarkResponse(BaseModel):
    vendor_id: int
    created_at: str

@router.post("/vendors/{vendor_id}")
async def bookmark_vendor(
    vendor_id: int,
    source_row_id: Optional[int] = None,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Add a vendor to the user's global Rolodex/favorites."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    existing = await session.exec(
        select(VendorBookmark)
        .where(VendorBookmark.user_id == auth_session.user_id)
        .where(VendorBookmark.vendor_id == vendor_id)
    )
    if not existing.first():
        bookmark = VendorBookmark(
            user_id=auth_session.user_id,
            vendor_id=vendor_id,
            source_row_id=source_row_id
        )
        session.add(bookmark)
        await session.commit()

    return {"status": "bookmarked", "vendor_id": vendor_id}

@router.delete("/vendors/{vendor_id}")
async def remove_vendor_bookmark(
    vendor_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Remove a vendor from favorites."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    existing = await session.exec(
        select(VendorBookmark)
        .where(VendorBookmark.user_id == auth_session.user_id)
        .where(VendorBookmark.vendor_id == vendor_id)
    )
    bookmark = existing.first()
    if bookmark:
        await session.delete(bookmark)
        await session.commit()

    return {"status": "removed", "vendor_id": vendor_id}

@router.get("/vendors", response_model=List[VendorBookmarkResponse])
async def get_vendor_bookmarks(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """List all favorited vendors for this user."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = await session.exec(
        select(VendorBookmark).where(VendorBookmark.user_id == auth_session.user_id)
    )
    bookmarks = results.all()
    
    return [
        VendorBookmarkResponse(
            vendor_id=b.vendor_id,
            created_at=b.created_at.isoformat()
        ) for b in bookmarks
    ]
