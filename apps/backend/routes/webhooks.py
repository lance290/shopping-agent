"""Webhook routes - GitHub, Railway, and Resend inbound webhooks."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import hmac
import hashlib

from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import BugReport

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature (HMAC SHA-256)."""
    if not signature:
        return False
    algo, sig = signature.split('=') if '=' in signature else ('sha256', signature)
    
    mac = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
    expected_sig = mac.hexdigest()
    return hmac.compare_digest(sig, expected_sig)


class WebhookPayload(BaseModel):
    action: Optional[str] = None
    pull_request: Optional[Dict[str, Any]] = None
    deployment_status: Optional[Dict[str, Any]] = None


@router.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """Handle GitHub webhooks (PR opened, merged)."""
    payload_bytes = await request.body()
    
    if WEBHOOK_SECRET != "dev-webhook-secret":
        if not verify_webhook_signature(payload_bytes, x_hub_signature_256 or ""):
            raise HTTPException(status_code=401, detail="Invalid signature")
            
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request")
    
    print(f"[WEBHOOK] Received GitHub event: {action}")
    
    if action == "opened" and pr:
        branch_name = pr.get("head", {}).get("ref", "")
        if branch_name.startswith("fix/bug-"):
            try:
                bug_id = int(branch_name.split("-")[-1])
                async for session in get_session():
                    bug = await session.get(BugReport, bug_id)
                    if bug:
                        bug.status = "pr_created"
                        bug.github_pr_url = pr.get("html_url")
                        session.add(bug)
                        await session.commit()
                        print(f"[WEBHOOK] Updated bug {bug_id} to pr_created")
            except Exception as e:
                print(f"[WEBHOOK] Failed to link PR to bug: {e}")

    if action == "closed" and pr and pr.get("merged"):
        branch_name = pr.get("head", {}).get("ref", "")
        if branch_name.startswith("fix/bug-"):
            try:
                bug_id = int(branch_name.split("-")[-1])
                async for session in get_session():
                    bug = await session.get(BugReport, bug_id)
                    if bug:
                        bug.status = "shipped"
                        session.add(bug)
                        await session.commit()
                        print(f"[WEBHOOK] Updated bug {bug_id} to shipped")
            except Exception as e:
                print(f"[WEBHOOK] Failed to link merged PR to bug: {e}")
    
    return {"status": "received"}


@router.post("/api/webhooks/railway")
async def railway_webhook(
    request: Request,
    x_railway_secret: Optional[str] = Header(None)
):
    """Handle Railway webhooks (Deployment success)."""
    if WEBHOOK_SECRET != "dev-webhook-secret":
        if x_railway_secret != WEBHOOK_SECRET:
             raise HTTPException(status_code=401, detail="Invalid secret")
             
    payload = await request.json()
    print(f"[WEBHOOK] Received Railway event: {payload.get('type')}")
    
    return {"status": "received"}


@router.api_route("/api/webhooks/ebay/account-deletion", methods=["GET", "POST"])
async def ebay_account_deletion_webhook(request: Request):
    """
    Handle eBay Marketplace Account Deletion/Closure Notifications.
    See: https://developer.ebay.com/marketplace-account-deletion
    """
    if request.method == "GET":
        # Handle the verification challenge from eBay
        challenge_code = request.query_params.get("challenge_code")
        if not challenge_code:
            raise HTTPException(status_code=400, detail="Missing challenge_code")
            
        verification_token = os.getenv("EBAY_VERIFICATION_TOKEN", "buy-anything-ebay-token-1234567890")
        
        # Determine the endpoint URL that eBay sent the request to
        # In production this will be the Railway URL, locally it might be different.
        # We try to construct it from the request headers to be exact.
        forwarded_proto = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("host", request.url.hostname)
        endpoint = f"{forwarded_proto}://{host}/api/webhooks/ebay/account-deletion"
        
        # Override with exact ENV var if provided (safest for eBay validation)
        exact_endpoint = os.getenv("EBAY_DELETION_ENDPOINT", endpoint)
        
        m = hashlib.sha256()
        m.update(challenge_code.encode('utf-8'))
        m.update(verification_token.encode('utf-8'))
        m.update(exact_endpoint.encode('utf-8'))
        
        return {"challengeResponse": m.hexdigest()}
        
    elif request.method == "POST":
        # Handle actual account deletion notification
        try:
            payload = await request.json()
            print(f"[WEBHOOK] Received eBay account deletion notification: {payload}")
            # We don't store eBay user data persistently linked to eBay accounts yet,
            # so we just acknowledge receipt with 200 OK.
            return {"status": "received"}
        except Exception as e:
            print(f"[WEBHOOK] Error processing eBay notification: {e}")
            # eBay requires a 200 OK even if we fail to process, to stop retries if it's our fault
            return {"status": "error"}


# ── Resend Inbound Webhook (Deal Pipeline Proxy Email) ──────────────────────

RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")


class ResendInboundAttachment(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None
    content: Optional[str] = None  # base64 encoded


class ResendInboundPayload(BaseModel):
    """Resend inbound email webhook payload."""
    from_: Optional[str] = None
    to: Optional[List[str]] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    message_id: Optional[str] = None

    class Config:
        populate_by_name = True
        # Resend sends "from" which is a Python reserved word
        fields = {"from_": {"alias": "from"}}


@router.post("/api/webhooks/resend/inbound")
async def resend_inbound_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Handle Resend inbound email webhooks for the deal pipeline proxy.

    When someone replies to a proxy alias (e.g. netjets-deal-42@messages.buy-anything.com),
    Resend POSTs the parsed email here. We:
    1. Resolve the deal from the alias
    2. Identify the sender (buyer or vendor)
    3. Record the message in the immutable ledger
    4. Relay the email to the other party
    """
    from services.deal_pipeline import (
        resolve_deal_from_alias,
        identify_sender,
        record_message,
        relay_email,
        classify_message,
        transition_deal_status,
    )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Resend wraps inbound email data inside {"type": "email.received", "data": {...}}
    event_type = payload.get("type", "")
    data = payload.get("data", payload)  # fall back to top-level if no wrapper
    
    logger.warning(f"[ResendWebhook] Event type: {event_type}, payload keys: {list(payload.keys())}")
    if "data" in payload:
        logger.warning(f"[ResendWebhook] data keys: {list(data.keys())}")
        # Log each field individually to avoid Railway truncation
        for k, v in data.items():
            val_str = str(v)[:300] if isinstance(v, str) else str(v)[:300]
            logger.warning(f"[ResendWebhook] data['{k}'] = {val_str}")

    from_email = data.get("from", "")
    email_id = data.get("email_id")  # needed to fetch body via API
    
    # Extract to list from data
    raw_to = data.get("to")
    if not raw_to:
        raw_to = data.get("rcpt_to", [])
        
    if isinstance(raw_to, str):
        to_list = [raw_to]
    elif isinstance(raw_to, list):
        to_list = raw_to
    else:
        to_list = []
        
    if not to_list:
        logger.warning(f"[ResendWebhook] 'to' is empty. data keys: {list(data.keys())}")
        
    subject = data.get("subject", "(no subject)")
    resend_msg_id = data.get("message_id") or email_id
    attachments_raw = data.get("attachments", [])
    
    # Try to get body from webhook payload first (some Resend plans include it)
    text_body = data.get("text", "") or ""
    html_body = data.get("html")
    
    # If no body in webhook, try fetching via Resend received emails API
    if not text_body and not html_body and email_id:
        try:
            import httpx
            resend_api_key = os.environ.get("RESEND_API_KEY", "")
            if resend_api_key:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.resend.com/emails/receiving/{email_id}",
                        headers={"Authorization": f"Bearer {resend_api_key}"},
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        email_data = resp.json()
                        text_body = email_data.get("text", "") or ""
                        html_body = email_data.get("html")
                        logger.info(f"[ResendWebhook] Fetched email body for {email_id}, text_len={len(text_body or '')}")
                    else:
                        logger.warning(f"[ResendWebhook] Received emails API returned {resp.status_code} for {email_id} — body not available")
        except Exception as e:
            logger.error(f"[ResendWebhook] Error fetching email body: {e}")
    
    logger.warning(f"[ResendWebhook] Body status: text_len={len(text_body)}, html={'yes' if html_body else 'no'}")

    # Extract the sender's actual email from "Name <email>" format
    import re
    email_match = re.search(r'<([^>]+)>', from_email)
    sender_email = email_match.group(1) if email_match else from_email

    # Extract alias from the To: address(es)
    alias = None
    for to_addr in to_list:
        addr_match = re.search(r'<([^>]+)>', to_addr)
        addr = addr_match.group(1) if addr_match else to_addr
        local_part = addr.split("@")[0] if "@" in addr else addr
        if local_part:
            alias = local_part
            break

    if not alias:
        logger.warning(f"[ResendWebhook] No alias found in To: {to_list}")
        return {"status": "ignored", "reason": "no_alias"}

    # Resolve the deal
    deal = await resolve_deal_from_alias(session, alias)
    if not deal:
        logger.warning(f"[ResendWebhook] No deal found for alias: {alias}")
        return {"status": "ignored", "reason": "unknown_alias"}

    # Identify sender
    sender_type = await identify_sender(deal, sender_email, session)
    if not sender_type:
        logger.warning(
            f"[ResendWebhook] Unrecognized sender {sender_email} for deal {deal.id}"
        )
        return {"status": "ignored", "reason": "unknown_sender"}

    # Process attachments (store metadata only for now)
    attachment_meta = []
    for att in attachments_raw:
        attachment_meta.append({
            "filename": att.get("filename", "unknown"),
            "content_type": att.get("content_type", "application/octet-stream"),
        })

    # Record in the immutable ledger
    msg = await record_message(
        session=session,
        deal_id=deal.id,
        sender_type=sender_type,
        content_text=text_body or "(no text content)",
        sender_email=sender_email,
        subject=subject,
        content_html=html_body,
        attachments=attachment_meta if attachment_meta else None,
        resend_message_id=resend_msg_id,
    )

    # AI classification (non-blocking — don't fail the webhook if LLM is down)
    ai_result = {"classification": "general", "confidence": 0.0, "extracted_price": None}
    try:
        ai_result = await classify_message(
            content_text=text_body or "",
            deal_context=f"Deal #{deal.id}, status={deal.status}",
        )
        # Update the message with AI analysis
        msg.ai_classification = ai_result.get("classification")
        msg.ai_confidence = ai_result.get("confidence")
        session.add(msg)
        await session.commit()
    except Exception as e:
        logger.warning(f"[ResendWebhook] AI classification error (non-fatal): {e}")

    # Auto-transition: if AI detects terms_agreed with high confidence
    # and the deal is still in negotiating status
    deal_transitioned = False
    if (
        ai_result.get("classification") == "terms_agreed"
        and ai_result.get("confidence", 0) >= 0.75
        and deal.status == "negotiating"
    ):
        try:
            await transition_deal_status(
                session=session,
                deal=deal,
                new_status="terms_agreed",
                vendor_quoted_price=ai_result.get("extracted_price"),
                agreed_terms_summary=ai_result.get("summary"),
            )
            deal_transitioned = True
            logger.info(f"[ResendWebhook] Auto-transitioned deal {deal.id} to terms_agreed")
        except Exception as e:
            logger.warning(f"[ResendWebhook] Auto-transition failed: {e}")

    # Relay to the other party
    relay_result = await relay_email(
        deal=deal,
        sender_type=sender_type,
        original_text=text_body or "",
        original_html=html_body,
        subject=subject,
        session=session,
    )

    logger.info(
        f"[ResendWebhook] deal={deal.id} sender={sender_type} "
        f"msg_id={msg.id} relay_ok={relay_result.success} "
        f"ai={ai_result.get('classification')}"
    )

    return {
        "status": "processed",
        "deal_id": deal.id,
        "message_id": msg.id,
        "sender_type": sender_type,
        "relayed": relay_result.success,
        "ai_classification": ai_result.get("classification"),
        "ai_confidence": ai_result.get("confidence"),
        "deal_transitioned": deal_transitioned,
    }
