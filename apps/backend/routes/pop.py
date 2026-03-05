import hmac
import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.auth import User
from models.rows import GroupThread, Project
from routes.pop_helpers import RESEND_WEBHOOK_SECRET, TWILIO_AUTH_TOKEN, _ensure_project_member
from routes import pop_notify
from routes import pop_processor
from routes.pop_list import list_router
from routes.pop_offers import offers_router
from routes.pop_wallet import wallet_router
from routes.pop_chat import chat_router
from routes.pop_referral import referral_router
from routes.pop_swaps import swaps_router

try:
    from twilio.request_validator import RequestValidator as TwilioValidator
except ModuleNotFoundError:  # pragma: no cover
    TwilioValidator = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pop", tags=["pop-chatbot"])

router.include_router(list_router)
router.include_router(offers_router)
router.include_router(wallet_router)
router.include_router(chat_router)
router.include_router(referral_router)
router.include_router(swaps_router)



@router.get("/health")
async def pop_health():
    """Health check for Pop/Bob service."""
    return {"status": "ok", "service": "pop"}


def _extract_twilio_media_urls(params: dict[str, Any]) -> list[str]:
    """Extract image media URLs from Twilio webhook params."""
    raw_count = params.get("NumMedia", "0")
    try:
        media_count = int(raw_count)
    except (TypeError, ValueError):
        media_count = 0

    image_urls: list[str] = []
    for idx in range(media_count):
        media_url = str(params.get(f"MediaUrl{idx}", "")).strip()
        media_type = str(params.get(f"MediaContentType{idx}", "")).lower()
        if media_url and media_type.startswith("image/"):
            image_urls.append(media_url)
    return image_urls


def _extract_resend_image_urls(payload: dict[str, Any]) -> list[str]:
    """Extract image attachment URLs from Resend inbound payload."""
    attachments = payload.get("attachments") or []
    if not isinstance(attachments, list):
        return []

    image_urls: list[str] = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        content_type = str(attachment.get("content_type") or attachment.get("mime_type") or "").lower()
        if not content_type or not content_type.startswith("image/"):
            continue

        for key in ("url", "content_url", "download_url", "href"):
            candidate = str(attachment.get(key) or "").strip()
            if candidate:
                image_urls.append(candidate)
                break
    return image_urls

def _verify_resend_signature(payload: bytes, signature: str) -> bool:
    """Verify Resend webhook signature using HMAC-SHA256."""
    if not RESEND_WEBHOOK_SECRET:
        logger.error("[Pop] RESEND_WEBHOOK_SECRET not set — rejecting webhook")
        return False
    expected = hmac.new(
        RESEND_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/resend")
async def resend_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Receives incoming emails to bob@buyanything.ai via Resend Inbound Webhooks.
    Resend posts JSON with the parsed email fields.
    Docs: https://resend.com/docs/dashboard/webhooks/introduction
    """
    raw_body = await request.body()
    signature = request.headers.get("resend-signature", "")

    if not _verify_resend_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    envelope = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    # Resend inbound webhook payload structure
    sender = envelope.get("from", "")
    # "from" may be a full address like "John <john@example.com>" — extract email
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]

    body = envelope.get("text", "") or envelope.get("html", "")
    subject = envelope.get("subject", "")
    image_urls = _extract_resend_image_urls(envelope)

    if not sender or (not body and not image_urls):
        raise HTTPException(status_code=400, detail="Missing sender and message content")

    if not body and image_urls:
        body = "User sent grocery photos. Extract items and add to list."

    logger.info(f"[Pop] Resend inbound from {sender}: {subject} (images={len(image_urls)})")

    background_tasks.add_task(
        pop_processor.process_pop_message,
        sender,
        body,
        session,
        "email",
        None,
        image_urls,
    )

    return {"status": "accepted"}

def _compute_thread_hash(phone_numbers: list[str]) -> str:
    """Compute a deterministic hash from sorted phone numbers for group thread identity.
    Pop's own number should be excluded before calling this.
    """
    sorted_nums = sorted(set(n.strip() for n in phone_numbers if n.strip()))
    key = ",".join(sorted_nums)
    return hashlib.sha256(key.encode()).hexdigest()[:32]


async def _resolve_group_thread(
    session: AsyncSession,
    from_phone: str,
    to_phones: list[str],
    user: "User",
) -> tuple["GroupThread | None", "Project | None"]:
    """Resolve or create a GroupThread for a group MMS conversation.
    Returns (group_thread, project) or (None, None) if not a group message.
    """
    from routes.pop_helpers import TWILIO_PHONE_NUMBER
    pop_number = TWILIO_PHONE_NUMBER
    human_phones = [p for p in ([from_phone] + to_phones) if p != pop_number]
    all_phones = sorted(set(human_phones))
    if len(all_phones) < 2:
        return None, None

    thread_hash = _compute_thread_hash(all_phones)
    stmt = select(GroupThread).where(GroupThread.thread_hash == thread_hash)
    result = await session.execute(stmt)
    gt = result.scalar_one_or_none()

    if gt:
        project = await session.get(Project, gt.project_id)
        if project:
            await _ensure_project_member(session, project.id, user.id, channel="sms")
            return gt, project

    proj_stmt = (
        select(Project)
        .where(Project.user_id == user.id)
        .where(Project.status == "active")
        .order_by(Project.updated_at.desc())
        .limit(1)
    )
    proj_result = await session.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        project = Project(title="My Shopping List", user_id=user.id)
        session.add(project)
        await session.commit()
        await session.refresh(project)

    gt = GroupThread(
        thread_hash=thread_hash,
        project_id=project.id,
        phone_numbers=",".join(all_phones),
    )
    session.add(gt)
    await _ensure_project_member(session, project.id, user.id, channel="sms")
    await session.commit()
    await session.refresh(gt)
    return gt, project


def _verify_twilio_signature(request: Request, form_data: dict) -> bool:
    """Verify Twilio request signature."""
    if not TWILIO_AUTH_TOKEN or TwilioValidator is None:
        logger.error("[Pop] Twilio auth token or SDK not available — rejecting webhook")
        return False
    validator = TwilioValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    return validator.validate(url, form_data, signature)


@router.post("/webhooks/twilio")
async def twilio_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Receives incoming SMS to Bob's phone number via Twilio.
    Twilio posts form-encoded data with From, Body, etc.
    Returns TwiML (empty <Response/>) to acknowledge receipt.
    """
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}

    if not _verify_twilio_signature(request, params):
        raise HTTPException(status_code=401, detail="Invalid Twilio signature")

    sender_phone = params.get("From", "")
    body = params.get("Body", "")
    image_urls = _extract_twilio_media_urls(params)

    if not sender_phone or (not body and not image_urls):
        raise HTTPException(status_code=400, detail="Missing From and message content")

    if not body and image_urls:
        body = "User sent grocery photos via SMS. Extract items and add to list."

    logger.info(f"[Pop] Twilio SMS from {sender_phone}: {body[:80]} (images={len(image_urls)})")

    # Look up user by phone number
    statement = select(User).where(User.phone_number == sender_phone)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user and user.email:
        # Detect group MMS: extract all To numbers
        to_raw = params.get("To", "")
        to_phones = [t.strip() for t in str(to_raw).split(",") if t.strip()]

        group_thread = None
        if len(to_phones) >= 2:
            group_thread, _project = await _resolve_group_thread(session, sender_phone, to_phones, user)
            if group_thread:
                logger.info(f"[Pop] Group MMS thread={group_thread.thread_hash[:8]} project={_project.id if _project else '?'}")

        background_tasks.add_task(
            pop_processor.process_pop_message,
            user.email,
            body,
            session,
            "sms",
            sender_phone,
            image_urls,
        )
    else:
        logger.info(f"[Pop] Unknown phone {sender_phone}. Sending onboarding SMS.")
        pop_notify.send_pop_onboarding_sms(sender_phone)

    # Return empty TwiML so Twilio doesn't retry
    return PlainTextResponse(
        content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
        media_type="application/xml",
    )