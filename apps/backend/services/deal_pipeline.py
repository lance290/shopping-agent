"""
Deal Pipeline Service: proxy email relay, deal lifecycle, and message ledger.

Handles:
- Creating deals with proxy email aliases
- Relaying inbound emails between buyer and vendor
- Recording every message in the immutable ledger
- Transitioning deal state
"""

import logging
import os
import re
import secrets
from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.deals import Deal, DealMessage
from models import Row, Bid, Vendor, User
from services.email import EmailResult, RESEND_API_KEY, FROM_NAME, DEV_EMAIL_OVERRIDE

try:
    import resend
except ModuleNotFoundError:  # pragma: no cover
    resend = None  # type: ignore

try:
    from email_reply_parser import EmailReplyParser
except ModuleNotFoundError:  # pragma: no cover
    EmailReplyParser = None  # type: ignore

logger = logging.getLogger(__name__)

MESSAGES_DOMAIN = os.getenv("DEAL_MESSAGES_DOMAIN", "messages.buy-anything.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3003")

TRUST_FOOTER_HTML = """
<hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
<p style="color: #999; font-size: 12px; line-height: 1.4;">
    This message is securely routed through <strong>BuyAnything</strong> to enable
    1-click escrow payments and buyer protection.<br>
    <a href="{app_url}/how-it-works" style="color: #999;">Learn more</a>
</p>
""".strip()

TRUST_FOOTER_TEXT = (
    "\n---\n"
    "This message is securely routed through BuyAnything to enable "
    "1-click escrow payments and buyer protection.\n"
    "Learn more: {app_url}/how-it-works"
)


def _build_legible_alias(vendor_name: str, deal_id: int) -> str:
    """
    Build a human-readable proxy alias like 'netjets-deal-284'.
    Per PRD: legible aliases reduce spam suspicion.
    """
    safe_name = re.sub(r"[^a-z0-9]+", "-", vendor_name.lower()).strip("-")[:20]
    return f"{safe_name}-deal-{deal_id}"


def _strip_reply(text: str) -> str:
    """Strip quoted reply chains from email text, keeping only the new content."""
    if EmailReplyParser is not None:
        reply = EmailReplyParser.parse_reply(text)
        if reply and reply.strip():
            return reply.strip()
    return text.strip()


async def create_deal(
    session: AsyncSession,
    row_id: int,
    buyer_user_id: int,
    bid_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
) -> Deal:
    """
    Create a new Deal record with a unique proxy email alias.
    Called when buyer initiates a quote request / negotiation.
    """
    # Validate row exists
    row = await session.get(Row, row_id)
    if not row:
        raise ValueError(f"Row {row_id} not found")

    # Resolve vendor from bid if not provided
    if bid_id and not vendor_id:
        bid = await session.get(Bid, bid_id)
        if bid:
            vendor_id = bid.vendor_id

    # Create deal with temporary alias
    deal = Deal(
        row_id=row_id,
        bid_id=bid_id,
        vendor_id=vendor_id,
        buyer_user_id=buyer_user_id,
        status="negotiating",
        proxy_email_alias=secrets.token_hex(4),  # Temporary, replaced after flush
    )
    session.add(deal)
    await session.flush()  # Get the deal.id

    # Now build the legible alias using vendor name + deal ID
    vendor_name = "vendor"
    if vendor_id:
        vendor = await session.get(Vendor, vendor_id)
        if vendor:
            vendor_name = vendor.name
    deal.proxy_email_alias = _build_legible_alias(vendor_name, deal.id)

    session.add(deal)
    await session.commit()
    await session.refresh(deal)

    logger.info(f"[DealPipeline] Created deal {deal.id} alias={deal.proxy_email_alias}@{MESSAGES_DOMAIN}")
    return deal


async def record_message(
    session: AsyncSession,
    deal_id: int,
    sender_type: str,
    content_text: str,
    sender_email: Optional[str] = None,
    subject: Optional[str] = None,
    content_html: Optional[str] = None,
    attachments: Optional[list] = None,
    resend_message_id: Optional[str] = None,
) -> DealMessage:
    """Save a message to the immutable ledger."""
    stripped_text = _strip_reply(content_text)

    msg = DealMessage(
        deal_id=deal_id,
        sender_type=sender_type,
        sender_email=sender_email,
        subject=subject,
        content_text=stripped_text,
        content_html=content_html,
        attachments=attachments,
        resend_message_id=resend_message_id,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def relay_email(
    deal: Deal,
    sender_type: str,
    original_text: str,
    original_html: Optional[str],
    subject: str,
    session: AsyncSession,
) -> EmailResult:
    """
    Relay an email through the proxy.
    - If sender is vendor -> relay to buyer
    - If sender is buyer -> relay to vendor
    """
    proxy_address = f"{deal.proxy_email_alias}@{MESSAGES_DOMAIN}"
    trust_footer_h = TRUST_FOOTER_HTML.format(app_url=APP_BASE_URL)
    trust_footer_t = TRUST_FOOTER_TEXT.format(app_url=APP_BASE_URL)

    # Determine recipient
    if sender_type == "vendor":
        # Relay to buyer
        buyer = await session.get(User, deal.buyer_user_id)
        if not buyer or not buyer.email:
            return EmailResult(success=False, error="Buyer email not found")
        to_email = buyer.email

        vendor_name = "Vendor"
        if deal.vendor_id:
            vendor = await session.get(Vendor, deal.vendor_id)
            if vendor:
                vendor_name = vendor.name
        from_display = f"{vendor_name} (via BuyAnything)"

    elif sender_type == "buyer":
        # Relay to vendor
        if not deal.vendor_id:
            return EmailResult(success=False, error="No vendor linked to deal")
        vendor = await session.get(Vendor, deal.vendor_id)
        if not vendor or not vendor.email:
            return EmailResult(success=False, error="Vendor email not found")
        to_email = vendor.email

        buyer = await session.get(User, deal.buyer_user_id)
        buyer_name = buyer.name if buyer and buyer.name else "Buyer"
        from_display = f"{buyer_name} (via BuyAnything)"

    else:
        return EmailResult(success=False, error=f"Invalid sender_type: {sender_type}")

    # DEV override
    if DEV_EMAIL_OVERRIDE:
        subject = f"[DEV → {to_email}] {subject}"
        to_email = DEV_EMAIL_OVERRIDE

    # Build HTML with trust footer
    html_body = original_html or f"<pre>{original_text}</pre>"
    html_body += trust_footer_h

    text_body = original_text + trust_footer_t

    # Send via Resend
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{from_display} <{proxy_address}>",
                "to": [to_email],
                "reply_to": proxy_address,
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            response = resend.Emails.send(params)
            logger.info(f"[DealPipeline] Relayed {sender_type} -> {to_email} for deal {deal.id}")
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            logger.error(f"[DealPipeline] Relay failed: {e}")
            return EmailResult(success=False, error=str(e))

    # Demo mode
    logger.info(f"[DealPipeline][DEMO] Would relay {sender_type} -> {to_email} | Subject: {subject}")
    return EmailResult(success=True, message_id=f"demo-relay-{deal.id}")


async def send_initial_outreach(
    deal: Deal,
    session: AsyncSession,
    request_summary: str,
) -> EmailResult:
    """
    Send the first outreach email to the vendor via the proxy alias.
    This kicks off the negotiation loop.
    """
    if not deal.vendor_id:
        return EmailResult(success=False, error="No vendor on deal")

    vendor = await session.get(Vendor, deal.vendor_id)
    if not vendor or not vendor.email:
        return EmailResult(success=False, error="Vendor email missing")

    buyer = await session.get(User, deal.buyer_user_id)
    buyer_name = buyer.name if buyer and buyer.name else "A buyer on BuyAnything"

    proxy_address = f"{deal.proxy_email_alias}@{MESSAGES_DOMAIN}"
    trust_footer_h = TRUST_FOOTER_HTML.format(app_url=APP_BASE_URL)

    subject = f"Quote Request: {request_summary}"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>New Quote Request</h2>
        <p>Hi {vendor.contact_name or vendor.name},</p>
        <p><strong>{buyer_name}</strong> is looking for a quote:</p>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>{request_summary}</strong></p>
        </div>
        <p>Simply reply to this email to start the conversation. All messages are securely routed.</p>
        {trust_footer_h}
    </div>
    """

    text_content = (
        f"New Quote Request\n\n"
        f"Hi {vendor.contact_name or vendor.name},\n\n"
        f"{buyer_name} is looking for a quote:\n\n"
        f"{request_summary}\n\n"
        f"Simply reply to this email to start the conversation.\n"
    )

    to_email = vendor.email
    if DEV_EMAIL_OVERRIDE:
        subject = f"[DEV → {to_email}] {subject}"
        to_email = DEV_EMAIL_OVERRIDE

    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{proxy_address}>",
                "to": [to_email],
                "reply_to": proxy_address,
                "subject": subject,
                "html": html_content,
                "text": text_content,
            }
            response = resend.Emails.send(params)
            logger.info(f"[DealPipeline] Initial outreach sent to {to_email} for deal {deal.id}")
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            logger.error(f"[DealPipeline] Initial outreach failed: {e}")
            return EmailResult(success=False, error=str(e))

    logger.info(f"[DealPipeline][DEMO] Would send initial outreach to {to_email} | Subject: {subject}")
    return EmailResult(success=True, message_id=f"demo-initial-{deal.id}")


async def transition_deal_status(
    session: AsyncSession,
    deal: Deal,
    new_status: str,
    **kwargs,
) -> Deal:
    """
    Transition a deal to a new status with timestamp updates.
    Valid transitions:
      negotiating -> terms_agreed -> funded -> in_transit -> completed
      any -> disputed, canceled
    """
    valid_transitions = {
        "negotiating": {"terms_agreed", "disputed", "canceled"},
        "terms_agreed": {"funded", "disputed", "canceled"},
        "funded": {"in_transit", "completed", "disputed", "canceled"},
        "in_transit": {"completed", "disputed", "canceled"},
        "completed": {"disputed"},
        "disputed": {"completed", "canceled"},
    }

    allowed = valid_transitions.get(deal.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: {deal.status} -> {new_status}. "
            f"Allowed: {allowed}"
        )

    deal.status = new_status
    deal.updated_at = datetime.utcnow()

    if new_status == "terms_agreed":
        deal.terms_agreed_at = datetime.utcnow()
        if "vendor_quoted_price" in kwargs and kwargs["vendor_quoted_price"] is not None:
            deal.vendor_quoted_price = kwargs["vendor_quoted_price"]
            deal.compute_buyer_total()
        if "agreed_terms_summary" in kwargs:
            deal.agreed_terms_summary = kwargs["agreed_terms_summary"]
    elif new_status == "funded":
        deal.funded_at = datetime.utcnow()
        if "stripe_payment_intent_id" in kwargs:
            deal.stripe_payment_intent_id = kwargs["stripe_payment_intent_id"]
    elif new_status == "completed":
        deal.completed_at = datetime.utcnow()
    elif new_status == "canceled":
        deal.canceled_at = datetime.utcnow()

    session.add(deal)
    await session.commit()
    await session.refresh(deal)

    logger.info(f"[DealPipeline] Deal {deal.id} transitioned to {new_status}")
    return deal


async def classify_message(
    content_text: str,
    deal_context: Optional[str] = None,
) -> dict:
    """
    Lightweight LLM classification of a deal message.
    Detects if terms have been agreed, a price was quoted, or it's general negotiation.

    Returns: {"classification": str, "confidence": float, "extracted_price": float|None, "summary": str}
    """
    from services.llm import call_gemini

    prompt = f"""You are analyzing a message in a buyer-vendor negotiation for a procurement deal.

Message:
\"\"\"
{content_text[:2000]}
\"\"\"

{f"Deal context: {deal_context}" if deal_context else ""}

Classify this message into ONE of these categories:
- "terms_agreed" — The vendor or buyer has explicitly confirmed a price, date, or terms (e.g. "Yes, we can do $14,000", "Deal, let's proceed at that price", "I accept your offer")
- "price_quoted" — A specific price or estimate was mentioned but not yet agreed (e.g. "We can offer this for $14,000", "Our rate would be...")
- "negotiating" — General back-and-forth, questions, clarifications, counteroffers
- "general" — Pleasantries, logistics, unrelated content

Also extract the price if one is mentioned (as a number, no currency symbol).

Return JSON ONLY, no extra text:
{{"classification": "...", "confidence": 0.0-1.0, "extracted_price": null or number, "summary": "one sentence summary of the message"}}"""

    try:
        import json
        result_text = await call_gemini(prompt, timeout=10.0)
        # Strip markdown code fences if present
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[-1]
        if result_text.endswith("```"):
            result_text = result_text.rsplit("```", 1)[0]
        result_text = result_text.strip()

        data = json.loads(result_text)
        return {
            "classification": data.get("classification", "general"),
            "confidence": float(data.get("confidence", 0.5)),
            "extracted_price": data.get("extracted_price"),
            "summary": data.get("summary", ""),
        }
    except Exception as e:
        logger.warning(f"[DealPipeline] AI classification failed: {e}")
        return {
            "classification": "general",
            "confidence": 0.0,
            "extracted_price": None,
            "summary": "",
        }


async def resolve_deal_from_alias(
    session: AsyncSession,
    alias: str,
) -> Optional[Deal]:
    """Look up a deal by its proxy email alias (the local part before @)."""
    result = await session.execute(
        select(Deal).where(Deal.proxy_email_alias == alias)
    )
    return result.scalar_one_or_none()


async def identify_sender(
    deal: Deal,
    from_email: str,
    session: AsyncSession,
) -> Optional[str]:
    """
    Determine if the sender is 'buyer' or 'vendor' based on their email.
    Returns None if unrecognized.
    """
    # Check buyer
    buyer = await session.get(User, deal.buyer_user_id)
    if buyer and buyer.email and buyer.email.lower() == from_email.lower():
        return "buyer"

    # Check vendor
    if deal.vendor_id:
        vendor = await session.get(Vendor, deal.vendor_id)
        if vendor and vendor.email and vendor.email.lower() == from_email.lower():
            return "vendor"

    return None
