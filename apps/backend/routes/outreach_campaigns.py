"""
Outreach campaign routes — draft, approve, send, pause, and view campaigns.

Level 1 MVP: EA-approved vendor outreach.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Bid, Row
from models.outreach import OutreachCampaign
from services.outreach_service import OutreachService

router = APIRouter(prefix="/outreach/campaigns", tags=["outreach"])
logger = logging.getLogger(__name__)


class DraftCampaignRequest(BaseModel):
    row_id: int
    ea_name: Optional[str] = "Executive Assistant"


class ApproveMessageRequest(BaseModel):
    edited_body: Optional[str] = None
    edited_subject: Optional[str] = None


@router.post("")
async def create_campaign(
    body: DraftCampaignRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Create a new outreach campaign with LLM-drafted messages for each vendor."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = auth_session.user_id

    # Get the row
    result = await session.exec(
        select(Row).where(Row.id == body.row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Get vendor bids for this row
    bids_result = await session.exec(
        select(Bid).where(
            Bid.row_id == body.row_id,
            Bid.source == "vendor_directory",
        )
    )
    vendor_bids = bids_result.all()

    if not vendor_bids:
        raise HTTPException(
            status_code=400,
            detail="No vendor results found for this row. Search must run first.",
        )

    service = OutreachService(session)
    campaign = await service.draft_campaign(
        row=row,
        user_id=user_id,
        vendor_bids=list(vendor_bids),
        ea_name=body.ea_name or "Executive Assistant",
    )

    # Return the full campaign with messages
    details = await service.get_campaign_with_messages(campaign.id, user_id)
    return details


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get campaign details with messages and quotes."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = OutreachService(session)
    details = await service.get_campaign_with_messages(campaign_id, auth_session.user_id)
    if not details:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return details


@router.get("/row/{row_id}")
async def get_campaigns_for_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get all campaigns for a row."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(OutreachCampaign).where(
            OutreachCampaign.row_id == row_id,
            OutreachCampaign.user_id == auth_session.user_id,
        )
    )
    campaigns = result.all()
    return [
        {
            "id": c.id,
            "status": c.status,
            "request_summary": c.request_summary,
            "action_budget": c.action_budget,
            "actions_used": c.actions_used,
            "created_at": c.created_at.isoformat(),
        }
        for c in campaigns
    ]


@router.post("/{campaign_id}/approve-all")
async def approve_all_messages(
    campaign_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Approve all draft messages in a campaign and send emails."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = OutreachService(session)
    try:
        messages = await service.approve_all(campaign_id, auth_session.user_id)
        sent_count = await service.send_approved_messages(campaign_id)
        return {
            "approved": len(messages),
            "sent": sent_count,
            "campaign_id": campaign_id,
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/messages/{message_id}/approve")
async def approve_message(
    message_id: int,
    body: ApproveMessageRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Approve a single message (optionally with edits)."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = OutreachService(session)
    try:
        message = await service.approve_message(
            message_id=message_id,
            user_id=auth_session.user_id,
            edited_body=body.edited_body,
            edited_subject=body.edited_subject,
        )
        return {
            "id": message.id,
            "status": message.status,
            "subject": message.subject,
            "body": message.body,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Message not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Emergency stop — pause all outreach for a campaign."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = OutreachService(session)
    try:
        campaign = await service.pause_campaign(campaign_id, auth_session.user_id)
        return {"id": campaign.id, "status": campaign.status}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/{campaign_id}/send")
async def send_campaign_messages(
    campaign_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Send all approved messages in a campaign."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify ownership
    campaign = await session.get(OutreachCampaign, campaign_id)
    if not campaign or campaign.user_id != auth_session.user_id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    service = OutreachService(session)
    sent_count = await service.send_approved_messages(campaign_id)
    return {"sent": sent_count, "campaign_id": campaign_id}
