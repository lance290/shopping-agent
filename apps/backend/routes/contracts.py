"""
DocuSign Contracts API routes.
Scaffold with demo mode (no live DocuSign API required for MVP).
"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Contract, User
from database import get_session
from dependencies import get_current_session

router = APIRouter(prefix="/contracts", tags=["contracts"])

DOCUSIGN_API_KEY = os.getenv("DOCUSIGN_API_KEY")


class ContractCreate(BaseModel):
    bid_id: Optional[int] = None
    row_id: Optional[int] = None
    quote_id: Optional[int] = None
    seller_email: str
    seller_company: Optional[str] = None
    deal_value: Optional[float] = None
    currency: str = "USD"
    template_id: Optional[str] = None


class ContractResponse(BaseModel):
    id: int
    status: str
    docusign_envelope_id: Optional[str]
    deal_value: Optional[float]
    seller_email: str
    seller_company: Optional[str]
    created_at: str


@router.post("")
async def create_contract(
    contract_data: ContractCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new contract and optionally send via DocuSign.
    Falls back to demo mode if DocuSign is not configured.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await session.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    contract = Contract(
        bid_id=contract_data.bid_id,
        row_id=contract_data.row_id,
        quote_id=contract_data.quote_id,
        buyer_user_id=auth_session.user_id,
        buyer_email=user.email,
        seller_email=contract_data.seller_email,
        seller_company=contract_data.seller_company,
        deal_value=contract_data.deal_value,
        currency=contract_data.currency,
        template_id=contract_data.template_id,
        status="draft",
    )

    # If DocuSign is configured, create envelope
    if DOCUSIGN_API_KEY:
        envelope_id = await _create_docusign_envelope(contract)
        contract.docusign_envelope_id = envelope_id
        contract.status = "sent"
        contract.sent_at = datetime.utcnow()
    else:
        # Demo mode: generate a fake envelope ID
        contract.docusign_envelope_id = f"demo-{uuid.uuid4().hex[:12]}"
        contract.status = "sent"
        contract.sent_at = datetime.utcnow()
        print(f"[DEMO DOCUSIGN] Contract created for {contract_data.seller_email}")
        print(f"[DEMO DOCUSIGN] Envelope: {contract.docusign_envelope_id}")

    session.add(contract)
    await session.commit()
    await session.refresh(contract)

    return ContractResponse(
        id=contract.id,
        status=contract.status,
        docusign_envelope_id=contract.docusign_envelope_id,
        deal_value=contract.deal_value,
        seller_email=contract.seller_email,
        seller_company=contract.seller_company,
        created_at=contract.created_at.isoformat(),
    )


@router.get("/{contract_id}")
async def get_contract(
    contract_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Get contract status."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contract = await session.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.buyer_user_id != auth_session.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return ContractResponse(
        id=contract.id,
        status=contract.status,
        docusign_envelope_id=contract.docusign_envelope_id,
        deal_value=contract.deal_value,
        seller_email=contract.seller_email,
        seller_company=contract.seller_company,
        created_at=contract.created_at.isoformat(),
    )


@router.post("/webhook/docusign")
async def docusign_webhook(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """
    DocuSign webhook handler for envelope status updates.
    Maps DocuSign events to contract status transitions.
    """
    envelope_id = payload.get("envelopeId") or payload.get("envelope_id")
    status = payload.get("status", "").lower()

    if not envelope_id:
        raise HTTPException(status_code=400, detail="Missing envelope ID")

    result = await session.execute(
        select(Contract).where(Contract.docusign_envelope_id == envelope_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        return {"status": "ignored", "reason": "Unknown envelope"}

    now = datetime.utcnow()
    status_map = {
        "delivered": ("viewed", "viewed_at"),
        "signed": ("signed", "signed_at"),
        "completed": ("completed", "completed_at"),
        "declined": ("declined", None),
        "voided": ("voided", None),
    }

    if status in status_map:
        new_status, timestamp_field = status_map[status]
        contract.status = new_status
        if timestamp_field:
            setattr(contract, timestamp_field, now)
        await session.commit()
        return {"status": "updated", "contract_status": new_status}

    return {"status": "ignored", "reason": f"Unhandled status: {status}"}


async def _create_docusign_envelope(contract: Contract) -> str:
    """
    Create a DocuSign envelope. Placeholder for real API integration.
    In production, this would call the DocuSign eSignature REST API.
    """
    # TODO: Implement real DocuSign API call
    # For now, return a demo envelope ID
    return f"ds-{uuid.uuid4().hex[:16]}"
