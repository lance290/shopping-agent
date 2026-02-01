"""Shares routes - endpoints for share link creation, resolution, and content access."""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import secrets
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import ShareLink, ShareSearchEvent, User, Row, Project, Bid
from routes.auth import get_current_session

router = APIRouter(tags=["shares"])


class ShareLinkCreate(BaseModel):
    """Request model for creating a share link."""
    resource_type: str  # "project", "row", "tile"
    resource_id: int


class ShareLinkResponse(BaseModel):
    """Response model for share link creation."""
    token: str
    share_url: str
    resource_type: str
    resource_id: int
    created_at: datetime


class ShareContentResponse(BaseModel):
    """Response model for shared content."""
    resource_type: str
    resource_id: int
    resource_data: Dict[str, Any]
    created_by: int
    access_count: int


class ShareMetricsResponse(BaseModel):
    """Response model for share metrics."""
    token: str
    access_count: int
    unique_visitors: int
    search_initiated_count: int
    search_success_count: int
    signup_conversion_count: int
    search_success_rate: float


def generate_share_token() -> str:
    """Generate a unique 32-character share token."""
    return secrets.token_urlsafe(24)[:32]


async def get_resource_data(
    resource_type: str,
    resource_id: int,
    session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Fetch resource data based on type and ID.

    Args:
        resource_type: Type of resource ("project", "row", "tile")
        resource_id: ID of the resource
        session: Database session

    Returns:
        Dictionary with resource data or None if not found
    """
    if resource_type == "project":
        result = await session.exec(select(Project).where(Project.id == resource_id))
        project = result.first()
        if project:
            return {
                "id": project.id,
                "title": project.title,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            }

    elif resource_type == "row":
        result = await session.exec(select(Row).where(Row.id == resource_id))
        row = result.first()
        if row:
            return {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "budget_max": row.budget_max,
                "currency": row.currency,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat()
            }

    elif resource_type == "tile" or resource_type == "bid":
        result = await session.exec(select(Bid).where(Bid.id == resource_id))
        bid = result.first()
        if bid:
            return {
                "id": bid.id,
                "item_title": bid.item_title,
                "price": bid.price,
                "currency": bid.currency,
                "item_url": bid.item_url,
                "image_url": bid.image_url,
                "condition": bid.condition
            }

    return None


@router.post("/api/shares")
async def create_share_link(
    share_create: ShareLinkCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> ShareLinkResponse:
    """
    Create a share link for a project, row, or tile.

    Requires authentication. Generates a unique token and returns the shareable URL.

    Args:
        share_create: Share link creation parameters
        authorization: Bearer token for authentication
        session: Database session

    Returns:
        ShareLinkResponse with token and share URL

    Raises:
        401: If not authenticated
        404: If resource not found
        400: If invalid resource type
    """
    # Verify authentication
    auth_session = await get_current_session(authorization, session)
    if not auth_session or not auth_session.user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate resource type
    if share_create.resource_type not in ["project", "row", "tile", "bid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource type: {share_create.resource_type}"
        )

    # Verify resource exists
    resource_data = await get_resource_data(
        share_create.resource_type,
        share_create.resource_id,
        session
    )
    if not resource_data:
        raise HTTPException(
            status_code=404,
            detail=f"Resource not found: {share_create.resource_type} #{share_create.resource_id}"
        )

    # Check if share link already exists for this resource
    result = await session.exec(
        select(ShareLink).where(
            ShareLink.resource_type == share_create.resource_type,
            ShareLink.resource_id == share_create.resource_id,
            ShareLink.created_by == auth_session.user_id
        )
    )
    existing_share = result.first()

    if existing_share:
        # Return existing share link
        return ShareLinkResponse(
            token=existing_share.token,
            share_url=f"/share/{existing_share.token}",
            resource_type=existing_share.resource_type,
            resource_id=existing_share.resource_id,
            created_at=existing_share.created_at
        )

    # Generate unique token
    token = generate_share_token()

    # Ensure token is unique
    while True:
        result = await session.exec(select(ShareLink).where(ShareLink.token == token))
        if not result.first():
            break
        token = generate_share_token()

    # Create share link
    share_link = ShareLink(
        token=token,
        resource_type=share_create.resource_type,
        resource_id=share_create.resource_id,
        created_by=auth_session.user_id,
        created_at=datetime.utcnow()
    )

    session.add(share_link)
    await session.commit()
    await session.refresh(share_link)

    return ShareLinkResponse(
        token=share_link.token,
        share_url=f"/share/{share_link.token}",
        resource_type=share_link.resource_type,
        resource_id=share_link.resource_id,
        created_at=share_link.created_at
    )


@router.get("/api/shares/{token}")
async def resolve_share_link(
    token: str,
    session: AsyncSession = Depends(get_session)
) -> ShareContentResponse:
    """
    Resolve a share link and return the shared content.

    Public endpoint - no authentication required.
    Increments access counters and tracks unique visitors.

    Args:
        token: Share link token
        session: Database session

    Returns:
        ShareContentResponse with shared content data

    Raises:
        404: If share link not found or resource no longer exists
    """
    # Find share link
    result = await session.exec(select(ShareLink).where(ShareLink.token == token))
    share_link = result.first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Get resource data
    resource_data = await get_resource_data(
        share_link.resource_type,
        share_link.resource_id,
        session
    )

    if not resource_data:
        raise HTTPException(
            status_code=404,
            detail="Shared content no longer available"
        )

    # Increment access count
    share_link.access_count += 1
    session.add(share_link)
    await session.commit()

    return ShareContentResponse(
        resource_type=share_link.resource_type,
        resource_id=share_link.resource_id,
        resource_data=resource_data,
        created_by=share_link.created_by,
        access_count=share_link.access_count
    )


@router.get("/api/shares/{token}/content")
async def get_share_content(
    token: str,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get the raw content of a shared resource (read-only).

    Public endpoint - no authentication required.

    Args:
        token: Share link token
        session: Database session

    Returns:
        Resource data as dictionary

    Raises:
        404: If share link not found or resource no longer exists
    """
    result = await session.exec(select(ShareLink).where(ShareLink.token == token))
    share_link = result.first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    resource_data = await get_resource_data(
        share_link.resource_type,
        share_link.resource_id,
        session
    )

    if not resource_data:
        raise HTTPException(status_code=404, detail="Shared content no longer available")

    return resource_data


@router.get("/api/shares/{token}/metrics")
async def get_share_metrics(
    token: str,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> ShareMetricsResponse:
    """
    Get analytics metrics for a share link.

    Requires authentication and ownership of the share link.

    Args:
        token: Share link token
        authorization: Bearer token for authentication
        session: Database session

    Returns:
        ShareMetricsResponse with analytics data

    Raises:
        401: If not authenticated
        403: If not the owner of the share link
        404: If share link not found
    """
    # Verify authentication
    auth_session = await get_current_session(authorization, session)
    if not auth_session or not auth_session.user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Find share link
    result = await session.exec(select(ShareLink).where(ShareLink.token == token))
    share_link = result.first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Verify ownership
    if share_link.created_by != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these metrics")

    # Calculate search success rate
    search_success_rate = 0.0
    if share_link.search_initiated_count > 0:
        search_success_rate = (
            share_link.search_success_count / share_link.search_initiated_count * 100
        )

    return ShareMetricsResponse(
        token=share_link.token,
        access_count=share_link.access_count,
        unique_visitors=share_link.unique_visitors,
        search_initiated_count=share_link.search_initiated_count,
        search_success_count=share_link.search_success_count,
        signup_conversion_count=share_link.signup_conversion_count,
        search_success_rate=round(search_success_rate, 2)
    )
