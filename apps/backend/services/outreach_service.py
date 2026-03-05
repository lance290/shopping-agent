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

OUTREACH_DOMAIN = os.getenv("OUTREACH_DOMAIN", "shopper.buy-anything.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3003")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


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
        ea_email: str = "",
        bid_ids: Optional[List[int]] = None,
    ) -> OutreachCampaign:
        """
        Create a new outreach campaign and draft messages for each vendor.

        Args:
            row: The row/request to create outreach for.
            user_id: The user who owns the row.
            vendor_bids: List of vendor bids to draft outreach for.
            ea_name: Name to sign emails with.
            ea_email: Email for reply-to.
            bid_ids: If provided, only draft for these specific bids.

        Returns:
            The created OutreachCampaign with draft messages.
        """
        # Filter to selected bids if specified
        if bid_ids:
            vendor_bids = [b for b in vendor_bids if b.id in bid_ids]

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
            reply_to = ea_email or f"{safe_prefix}-{campaign_hash}@{OUTREACH_DOMAIN}"

            # Determine contact channel
            contact_email = getattr(vendor, "contact_email", None) or getattr(vendor, "email", None)
            channel = "email" if contact_email else "manual"

            # Classify vendor type + draft email in one LLM call
            vendor_desc = getattr(vendor, "description", "") or ""
            vendor_category = getattr(vendor, "category", "") or ""
            draft = await self._classify_and_draft(
                request_summary=request_summary,
                constraints=constraints,
                vendor_name=vendor.name,
                vendor_description=vendor_desc,
                vendor_category=vendor_category,
                ea_name=ea_name,
                row_title=row.title,
            )

            subject = draft["subject"]
            body = draft["body"]

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

    async def _classify_and_draft(
        self,
        request_summary: str,
        constraints: str,
        vendor_name: str,
        vendor_description: str,
        vendor_category: str,
        ea_name: str,
        row_title: str,
    ) -> Dict[str, str]:
        """LLM classifies vendor type and drafts a category-appropriate email in one call."""
        prompt = f"""You are drafting an outreach email on behalf of "{ea_name}" to request
a quote from a vendor. First classify the vendor type from context, then write the email.

== CONTEXT ==
Request: {request_summary}
Constraints: {constraints}
Vendor: {vendor_name}
Vendor description: {vendor_description}
Vendor category: {vendor_category}

== INSTRUCTIONS ==
1. Classify this vendor into one of: private_aviation, yacht, luxury_goods, supercar,
   local_service, retail, wholesale, or other.
2. Draft a professional outreach email appropriate for this vendor type:
   - private_aviation: formal RFP style — request tail numbers, safety certs (ARGUS/Wyvern),
     itemized pricing, repositioning fees, connectivity (Wi-Fi/Starlink), cancellation policy.
   - yacht: formal RFP — request vessel specs, crew details, itinerary options, APA estimate,
     insurance, port fees.
   - luxury_goods: concierge tone — request availability, authentication, pricing, shipping.
   - supercar: concierge tone — request availability, specs, pricing, delivery options, warranty.
   - local_service: friendly professional — request estimate, availability, timeline, references.
   - retail / wholesale / other: brief professional — request pricing, availability, shipping.
3. Include ALL relevant details from the request. Do NOT invent details not provided.
4. Sign as: {ea_name}
5. Keep it under 250 words.

Return JSON ONLY:
{{{{
  "vendor_type": "...",
  "subject": "...",
  "body": "..."
}}}}"""

        try:
            text = await call_gemini(prompt, timeout=20.0)
            # Strip markdown fences if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
            cleaned = re.sub(r"```\s*$", "", cleaned)
            parsed = json.loads(cleaned)
            return {
                "vendor_type": parsed.get("vendor_type", "other"),
                "subject": parsed.get("subject", f"Inquiry: {row_title}"),
                "body": parsed.get("body", ""),
            }
        except Exception as e:
            logger.error(f"[OutreachService] LLM classify+draft failed: {e}")
            return {
                "vendor_type": "other",
                "subject": f"Inquiry: {row_title}",
                "body": (
                    f"Hi,\n\n"
                    f"We are looking for: {request_summary}\n\n"
                    f"Could you please provide availability and pricing?\n\n"
                    f"Best regards,\n{ea_name}"
                ),
            }

    def _build_deal_card_html(self, campaign: OutreachCampaign) -> str:
        """Build an HTML deal card summarizing the buyer request for the vendor."""
        summary = campaign.request_summary or ""
        constraints_raw = campaign.structured_constraints or "{}"
        try:
            constraints = json.loads(constraints_raw) if isinstance(constraints_raw, str) else constraints_raw
        except (json.JSONDecodeError, TypeError):
            constraints = {}

        details_html = ""
        if isinstance(constraints, dict):
            for key, val in constraints.items():
                if val and str(val).lower() not in ("not answered", "none", "null", "{}"):
                    label = key.replace("_", " ").title()
                    details_html += f'<tr><td style="padding:4px 12px 4px 0;color:#64748b;font-size:13px;">{label}</td><td style="padding:4px 0;font-size:13px;color:#1e293b;">{val}</td></tr>'

        return f"""
        <div style="border:1px solid #e2e8f0; border-radius:12px; overflow:hidden; margin:24px 0; max-width:520px;">
            <div style="background:linear-gradient(135deg,#1e293b 0%,#334155 100%); padding:16px 20px;">
                <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#fbbf24;font-weight:700;">Deal Card</p>
                <p style="margin:6px 0 0;font-size:16px;font-weight:700;color:#ffffff;">{summary}</p>
            </div>
            {'<table style="width:100%;padding:16px 20px;border-spacing:0;">' + details_html + '</table>' if details_html else ''}
            <div style="padding:12px 20px 16px;background:#f8fafc;text-align:center;">
                <p style="margin:0;font-size:12px;color:#64748b;">Powered by <strong>BuyAnything.ai</strong></p>
            </div>
        </div>
        """

    async def _send_email(self, message: OutreachMessage) -> bool:
        """Send an email via Resend with HTML body, deal card, and viral footer."""
        if not RESEND_API_KEY:
            logger.warning("[OutreachService] RESEND_API_KEY not configured — email not sent")
            return False

        # Build HTML version of the body
        body_html = message.body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body_html = "<br>\n".join(body_html.split("\n"))

        # Attach deal card if campaign is available
        deal_card_html = ""
        try:
            campaign = await self.session.get(OutreachCampaign, message.campaign_id)
            if campaign:
                deal_card_html = self._build_deal_card_html(campaign)
        except Exception:
            pass

        # Viral footer
        from services.email import _viral_footer_html, _viral_footer_text

        html_content = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="line-height: 1.6;">{body_html}</div>
            {deal_card_html}
            {_viral_footer_html()}
        </body>
        </html>
        """

        plain_text = f"{message.body}\n{_viral_footer_text()}"

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
                        "html": html_content,
                        "text": plain_text,
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
