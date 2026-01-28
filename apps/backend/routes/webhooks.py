"""Webhook routes - GitHub and Railway webhooks."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import hmac
import hashlib

from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import BugReport

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
