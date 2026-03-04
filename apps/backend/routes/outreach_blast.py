"""
Blast outreach route — send a single template to ALL vendors in a row.

Extracted from routes/outreach.py to keep files under 450 lines.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from models import (
    Row, SellerQuote, OutreachEvent, User,
    generate_magic_link_token,
)
from database import get_session
from dependencies import get_current_session
from services.email import send_admin_vendor_alert

router = APIRouter(prefix="/outreach", tags=["outreach"])


class BlastRequest(BaseModel):
    subject: str
    body: str
    dry_run: bool = False


@router.post("/rows/{row_id}/blast")
async def blast_outreach(
    row_id: int,
    request: BlastRequest,
    authorization: Optional[str] = Header(None),
    session=Depends(get_session),
):
    """
    Send a single email template to ALL vendors in a row.
    Template placeholders: {{vendor_name}}, {{vendor_company}}, {{row_title}}
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_result = await session.execute(select(User).where(User.id == auth_session.user_id))
    user = user_result.scalar_one_or_none()

    if not user or not user.email:
        raise HTTPException(
            status_code=422,
            detail="Please add your email address to your profile before sending outreach.",
        )
    if not user.name:
        raise HTTPException(
            status_code=422,
            detail="Please add your name to your profile before sending outreach.",
        )

    reply_to_email = user.email
    sender_name = user.name

    result = await session.execute(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    from models import Vendor, Bid
    bids_result = await session.execute(
        select(Bid).where(
            Bid.row_id == row_id,
            Bid.vendor_id.isnot(None),
            Bid.is_superseded == False,
        )
    )
    vendor_bids = bids_result.scalars().all()

    seen_vendor_ids = set()
    targets = []
    for bid in vendor_bids:
        if bid.vendor_id in seen_vendor_ids:
            continue
        seen_vendor_ids.add(bid.vendor_id)
        v_result = await session.execute(select(Vendor).where(Vendor.id == bid.vendor_id))
        vendor = v_result.scalar_one_or_none()
        if vendor and vendor.email:
            targets.append({
                "vendor_id": vendor.id,
                "vendor_name": vendor.contact_name or vendor.name,
                "vendor_company": vendor.name,
                "vendor_email": vendor.email,
                "bid_id": bid.id,
            })

    existing_result = await session.execute(
        select(OutreachEvent.vendor_email).where(
            OutreachEvent.row_id == row_id,
            OutreachEvent.sent_at.isnot(None),
        )
    )
    already_contacted = {r[0].lower() for r in existing_result.all()}
    new_targets = [t for t in targets if t["vendor_email"].lower() not in already_contacted]

    if not new_targets:
        return {
            "status": "no_new_vendors",
            "row_id": row_id,
            "total_vendors": len(targets),
            "already_contacted": len(already_contacted),
            "sent": 0,
        }

    if request.dry_run:
        previews = []
        for t in new_targets:
            subj = request.subject.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
            bod = request.body.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
            previews.append({"to": t["vendor_email"], "subject": subj, "body_preview": bod[:200]})
        return {
            "status": "dry_run",
            "row_id": row_id,
            "would_send": len(new_targets),
            "already_contacted": len(already_contacted),
            "previews": previews,
        }

    from services.email import send_custom_outreach_email, get_quote_url, get_tracking_pixel_url
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    sent = []
    failed = []
    for t in new_targets:
        token = generate_magic_link_token()

        quote = SellerQuote(
            row_id=row_id,
            token=token,
            token_expires_at=datetime.utcnow() + timedelta(days=14),
            seller_email=t["vendor_email"],
            seller_name=t["vendor_name"],
            seller_company=t["vendor_company"],
            status="pending",
        )
        session.add(quote)

        event = OutreachEvent(
            row_id=row_id,
            vendor_email=t["vendor_email"],
            vendor_name=t["vendor_name"],
            vendor_company=t["vendor_company"],
            vendor_source="blast",
            quote_token=token,
        )
        session.add(event)

        subj = request.subject.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")
        body_text = request.body.replace("{{vendor_name}}", t["vendor_name"]).replace("{{vendor_company}}", t["vendor_company"]).replace("{{row_title}}", row.title or "")

        quote_url = get_quote_url(token)
        tracking_url = get_tracking_pixel_url(token)
        unsubscribe_url = f"{backend_url}/outreach/unsubscribe/{token}"

        body_html = body_text.replace("\n", "<br>")
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto;">
            {body_html}
            <p style="text-align: center; margin: 30px 0;">
                <a href="{quote_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Submit Your Quote</a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #999; font-size: 12px;">Sent on behalf of {sender_name} via BuyAnything<br><a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a></p>
            <p style="color: #bbb; font-size: 10px;">BuyAnything.ai is a marketplace platform. We may earn a referral fee or commission when transactions are completed through our platform.</p>
            <img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">
        </div>
        """

        email_result = await send_custom_outreach_email(
            to_email=t["vendor_email"],
            vendor_company=t["vendor_company"],
            subject=subj,
            body_text=body_text,
            quote_token=token,
            reply_to_email=reply_to_email,
            sender_name=sender_name,
        )

        if email_result.success:
            event.sent_at = datetime.utcnow()
            event.message_id = email_result.message_id
            sent.append({"vendor": t["vendor_company"], "email": t["vendor_email"]})
        else:
            failed.append({"vendor": t["vendor_company"], "email": t["vendor_email"], "error": email_result.error})

    row.outreach_status = "in_progress"
    row.outreach_count = (row.outreach_count or 0) + len(sent)
    await session.commit()

    await send_admin_vendor_alert(
        event_type="blast_sent",
        vendor_name=f"{len(sent)} vendors",
        row_title=row.title,
        row_id=row_id,
    )

    return {
        "status": "success",
        "row_id": row_id,
        "sent": len(sent),
        "failed": len(failed),
        "already_contacted": len(already_contacted),
        "details": sent,
        "errors": failed if failed else None,
    }
