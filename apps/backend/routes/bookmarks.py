import json
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode
from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from database import get_session
from dependencies import get_current_session
from models import Vendor, Row, Bid, RequestEvent
from models.bookmarks import VendorBookmark, ItemBookmark
from pydantic import BaseModel

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

class VendorBookmarkResponse(BaseModel):
    vendor_id: int
    created_at: str


class ItemBookmarkRequest(BaseModel):
    canonical_url: str
    source_row_id: Optional[int] = None


class ItemBookmarkResponse(BaseModel):
    canonical_url: str
    created_at: str


def _normalize_bookmark_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    try:
        parsed = urlsplit(candidate)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in {
                "tag", "ref", "ref_", "fbclid", "gclid", "mc_cid", "mc_eid", "aff", "aff_id", "clickid"
            }
        ]
        normalized_path = parsed.path.rstrip("/") or parsed.path or "/"
        return urlunsplit(("https", host, normalized_path, urlencode(filtered_query, doseq=True), ""))
    except Exception:
        return candidate


async def _sync_vendor_bookmark_like_state(
    session: AsyncSession,
    user_id: int,
    vendor_id: int,
    is_bookmarked: bool,
) -> None:
    result = await session.exec(
        select(Bid).where(
            Bid.vendor_id == vendor_id,
            Bid.row_id.in_(select(Row.id).where(Row.user_id == user_id)),
        )
    )
    for bid in result.all():
        bid.is_liked = is_bookmarked
        if not is_bookmarked:
            bid.liked_at = None


async def _sync_item_bookmark_like_state(
    session: AsyncSession,
    user_id: int,
    canonical_url: str,
    is_bookmarked: bool,
) -> None:
    result = await session.exec(
        select(Bid).where(
            Bid.row_id.in_(select(Row.id).where(Row.user_id == user_id)),
            or_(Bid.canonical_url.isnot(None), Bid.item_url.isnot(None)),
        )
    )
    for bid in result.all():
        bid_url = _normalize_bookmark_url(bid.canonical_url or bid.item_url)
        if bid_url == canonical_url:
            bid.is_liked = is_bookmarked
            if not is_bookmarked:
                bid.liked_at = None

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
    await _sync_vendor_bookmark_like_state(session, auth_session.user_id, vendor_id, True)

    # Trust event: candidate_saved (PRD §9 implicit feedback)
    if source_row_id is not None:
        session.add(RequestEvent(
            row_id=source_row_id,
            user_id=auth_session.user_id,
            event_type="candidate_saved",
            event_value="vendor_bookmark",
            metadata_json=json.dumps({"vendor_id": vendor_id}),
        ))
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
    await _sync_vendor_bookmark_like_state(session, auth_session.user_id, vendor_id, False)
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


@router.post("/items")
async def bookmark_item(
    payload: ItemBookmarkRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    canonical_url = _normalize_bookmark_url(payload.canonical_url)
    if not canonical_url:
        raise HTTPException(status_code=400, detail="canonical_url is required")

    existing = await session.exec(
        select(ItemBookmark)
        .where(ItemBookmark.user_id == auth_session.user_id)
        .where(ItemBookmark.canonical_url == canonical_url)
    )
    if not existing.first():
        bookmark = ItemBookmark(
            user_id=auth_session.user_id,
            canonical_url=canonical_url,
            source_row_id=payload.source_row_id,
        )
        session.add(bookmark)
    await _sync_item_bookmark_like_state(session, auth_session.user_id, canonical_url, True)

    # Trust event: candidate_saved (PRD §9 implicit feedback)
    if payload.source_row_id is not None:
        session.add(RequestEvent(
            row_id=payload.source_row_id,
            user_id=auth_session.user_id,
            event_type="candidate_saved",
            event_value="item_bookmark",
            metadata_json=json.dumps({"canonical_url": canonical_url}),
        ))
    await session.commit()

    return {"status": "bookmarked", "canonical_url": canonical_url}


@router.delete("/items")
async def remove_item_bookmark(
    payload: ItemBookmarkRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    canonical_url = _normalize_bookmark_url(payload.canonical_url)
    if not canonical_url:
        raise HTTPException(status_code=400, detail="canonical_url is required")

    existing = await session.exec(
        select(ItemBookmark)
        .where(ItemBookmark.user_id == auth_session.user_id)
        .where(ItemBookmark.canonical_url == canonical_url)
    )
    bookmark = existing.first()
    if bookmark:
        await session.delete(bookmark)
    await _sync_item_bookmark_like_state(session, auth_session.user_id, canonical_url, False)
    await session.commit()

    return {"status": "removed", "canonical_url": canonical_url}


@router.get("/items", response_model=List[ItemBookmarkResponse])
async def get_item_bookmarks(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = await session.exec(
        select(ItemBookmark).where(ItemBookmark.user_id == auth_session.user_id)
    )
    bookmarks = results.all()

    return [
        ItemBookmarkResponse(
            canonical_url=b.canonical_url,
            created_at=b.created_at.isoformat(),
        ) for b in bookmarks
    ]
