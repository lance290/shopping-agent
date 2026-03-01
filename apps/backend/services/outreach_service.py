"""
Outreach Service — draft, approve, and send vendor outreach campaigns.

Level 1 MVP: Draft & Send
- LLM drafts personalized outreach per vendor
- EA reviews and approves
- System sends approved emails via Resend
"""

import json
import logging
import os
import re
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row, Vendor
from models.outreach import OutreachCampaign, OutreachMessage, OutreachQuote
from services.llm import call_gemini

logger = logging.getLogger(__name__)

OUTREACH_DOMAIN = os.getenv("OUTREACH_DOMAIN", "quotes.buyanything.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")


class OutreachService:
    """Orchestrates vendor outreach campaigns."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def draft_campaign(
        self,
        row: Row,
        user_id: int,
        vendor_bids: List[Bid],
        ea_name: str = "Executive Assistant",
    ) -> OutreachCampaign:
        """
        Create a new outreach campaign and draft messages for each vendor.

        Args:
            row: The row/request to create outreach for.
            user_id: The user who owns the row.
            vendor_bids: List of vendor bids to draft outreach for.
            ea_name: Name to sign emails with.

        Returns:
            The created OutreachCampaign with draft messages.
        """
        # Build request summary from row data
        request_summary = await self._build_request_summary(row)
        constraints = row.structured_constraints or row.choice_answers or "{}"

        campaign = OutreachCampaign(
            row_id=row.id,
            user_id=user_id,
            status="draft",
            request_summary=request_summary,
            structured_constraints=constraints,
            action_budget=min(20, len(vendor_bids)),
            actions_used=0,
        )
        self.session.add(campaign)
        await self.session.flush()

        # Draft a message for each vendor
        for bid in vendor_bids:
            if not bid.vendor_id:
                continue

            vendor = await self.session.get(Vendor, bid.vendor_id)
            if not vendor:
                continue

            # Generate unique reply-to address for this campaign
            campaign_hash = secrets.token_hex(4)
            safe_prefix = re.sub(r'[^a-z0-9-]', '', row.title[:20].lower().replace(' ', '-'))
            reply_to = f"{safe_prefix}-{campaign_hash}@{OUTREACH_DOMAIN}"

            # Determine contact channel
            contact_email = getattr(vendor, "contact_email", None) or getattr(vendor, "email", None)
            channel = "email" if contact_email else "manual"

            # Draft the message using LLM
            body = await self._draft_outreach_message(
                request_summary=request_summary,
                constraints=constraints,
                vendor_name=vendor.name,
                vendor_description=getattr(vendor, "description", "") or "",
                ea_name=ea_name,
            )

            subject = f"Inquiry: {row.title}"

            message = OutreachMessage(
                campaign_id=campaign.id,
                vendor_id=vendor.id,
                bid_id=bid.id,
                direction="outbound",
                channel=channel,
                status="draft",
                subject=subject,
                body=body,
                to_address=contact_email or "",
                reply_to_address=reply_to,
            )
            self.session.add(message)

        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def approve_message(
        self,
        message_id: int,
        user_id: int,
        edited_body: Optional[str] = None,
        edited_subject: Optional[str] = None,
    ) -> OutreachMessage:
        """Approve a draft message (optionally with edits). Queues for sending."""
        result = await self.session.exec(
            select(OutreachMessage).where(OutreachMessage.id == message_id)
        )
        message = result.first()
        if not message:
            raise ValueError(f"Message {message_id} not found")

        # Verify ownership via campaign
        campaign = await self.session.get(OutreachCampaign, message.campaign_id)
        if not campaign or campaign.user_id != user_id:
            raise PermissionError("Not authorized")

        if edited_body:
            message.body = edited_body
        if edited_subject:
            message.subject = edited_subject

        message.status = "approved"
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def approve_all(self, campaign_id: int, user_id: int) -> List[OutreachMessage]:
        """Approve all draft messages in a campaign."""
        campaign = await self.session.get(OutreachCampaign, campaign_id)
        if not campaign or campaign.user_id != user_id:
            raise PermissionError("Not authorized")

        result = await self.session.exec(
            select(OutreachMessage).where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.status == "draft",
            )
        )
        messages = result.all()
        for msg in messages:
            msg.status = "approved"
            self.session.add(msg)

        campaign.status = "active"
        campaign.updated_at = datetime.utcnow()
        self.session.add(campaign)

        await self.session.commit()
        return list(messages)

    async def send_approved_messages(self, campaign_id: int) -> int:
        """Send all approved messages via email. Returns count of sent messages."""
        result = await self.session.exec(
            select(OutreachMessage).where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.status == "approved",
                OutreachMessage.channel == "email",
            )
        )
        messages = result.all()
        sent_count = 0

        for msg in messages:
            success = await self._send_email(msg)
            if success:
                msg.status = "sent"
                msg.sent_at = datetime.utcnow()
                sent_count += 1
            else:
                msg.status = "failed"
            self.session.add(msg)

        # Update campaign action count
        campaign = await self.session.get(OutreachCampaign, campaign_id)
        if campaign:
            campaign.actions_used += sent_count
            campaign.updated_at = datetime.utcnow()
            self.session.add(campaign)

        await self.session.commit()
        logger.info(f"[OutreachService] Campaign {campaign_id}: sent {sent_count}/{len(messages)} emails")
        return sent_count

    async def pause_campaign(self, campaign_id: int, user_id: int) -> OutreachCampaign:
        """Emergency stop — pause all outreach for a campaign."""
        campaign = await self.session.get(OutreachCampaign, campaign_id)
        if not campaign or campaign.user_id != user_id:
            raise PermissionError("Not authorized")

        campaign.status = "paused"
        campaign.updated_at = datetime.utcnow()
        self.session.add(campaign)

        # Hold all queued messages
        result = await self.session.exec(
            select(OutreachMessage).where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.status == "approved",
            )
        )
        for msg in result.all():
            msg.status = "draft"  # Revert to draft
            self.session.add(msg)

        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def get_campaign_with_messages(
        self, campaign_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get campaign details with all messages and quotes."""
        campaign = await self.session.get(OutreachCampaign, campaign_id)
        if not campaign or campaign.user_id != user_id:
            return None

        messages_result = await self.session.exec(
            select(OutreachMessage).where(OutreachMessage.campaign_id == campaign_id)
        )
        messages = messages_result.all()

        quotes_result = await self.session.exec(
            select(OutreachQuote).where(OutreachQuote.campaign_id == campaign_id)
        )
        quotes = quotes_result.all()

        # Build vendor lookup
        vendor_ids = {m.vendor_id for m in messages}
        vendors = {}
        for vid in vendor_ids:
            v = await self.session.get(Vendor, vid)
            if v:
                vendors[vid] = {"id": v.id, "name": v.name, "domain": getattr(v, "domain", None)}

        return {
            "campaign": {
                "id": campaign.id,
                "row_id": campaign.row_id,
                "status": campaign.status,
                "request_summary": campaign.request_summary,
                "action_budget": campaign.action_budget,
                "actions_used": campaign.actions_used,
                "created_at": campaign.created_at.isoformat(),
            },
            "messages": [
                {
                    "id": m.id,
                    "vendor_id": m.vendor_id,
                    "vendor": vendors.get(m.vendor_id, {}),
                    "direction": m.direction,
                    "channel": m.channel,
                    "status": m.status,
                    "subject": m.subject,
                    "body": m.body,
                    "to_address": m.to_address,
                    "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                }
                for m in messages
            ],
            "quotes": [
                {
                    "id": q.id,
                    "vendor_id": q.vendor_id,
                    "vendor": vendors.get(q.vendor_id, {}),
                    "price": q.price,
                    "currency": q.currency,
                    "availability": q.availability,
                    "terms": q.terms,
                    "entry_method": q.entry_method,
                    "is_finalist": q.is_finalist,
                }
                for q in quotes
            ],
        }

    # === Private helpers ===

    async def _build_request_summary(self, row: Row) -> str:
        """Build a human-readable request summary from row data."""
        parts = [row.title]
        if row.choice_answers:
            try:
                answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                if isinstance(answers, dict):
                    for key, val in answers.items():
                        if val and str(val).lower() not in ("not answered", "none", "null"):
                            label = key.replace("_", " ").title()
                            parts.append(f"{label}: {val}")
            except (json.JSONDecodeError, TypeError):
                pass
        return " | ".join(parts)

    async def _draft_outreach_message(
        self,
        request_summary: str,
        constraints: str,
        vendor_name: str,
        vendor_description: str,
        ea_name: str,
    ) -> str:
        """Use LLM to draft a professional outreach email."""
        prompt = f"""You are drafting an outreach email on behalf of an executive assistant.

Request details: {request_summary}
Structured constraints: {constraints}

Vendor: {vendor_name}
Vendor description: {vendor_description}

Write a professional, concise email requesting availability and pricing.
Include all relevant details from the request.
Sign as: {ea_name}

Tone: Professional but warm. This is a business inquiry, not a cold sales email.
Do NOT include made-up details. Only use information provided.
Do NOT include a subject line — just the email body.
Keep it under 200 words.

Return ONLY the email body text, no JSON or markdown."""

        try:
            body = await call_gemini(prompt, timeout=15.0)
            return body.strip()
        except Exception as e:
            logger.error(f"[OutreachService] LLM draft failed: {e}")
            # Fallback: simple template
            return (
                f"Hi,\n\n"
                f"We are looking for: {request_summary}\n\n"
                f"Could you please provide availability and pricing?\n\n"
                f"Best regards,\n{ea_name}"
            )

    async def _send_email(self, message: OutreachMessage) -> bool:
        """Send an email via Resend. Returns True on success."""
        if not RESEND_API_KEY:
            logger.warning("[OutreachService] RESEND_API_KEY not configured — email not sent")
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"BuyAnything <outreach@{OUTREACH_DOMAIN}>",
                        "to": [message.to_address],
                        "subject": message.subject or "Inquiry",
                        "text": message.body,
                        "reply_to": message.reply_to_address,
                    },
                    timeout=10.0,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    message.metadata_json = json.dumps({"resend_id": data.get("id")})
                    logger.info(f"[OutreachService] Email sent to {message.to_address}")
                    return True
                else:
                    logger.error(f"[OutreachService] Resend failed: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"[OutreachService] Email send error: {e}")
            return False
