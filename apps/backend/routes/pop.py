import hmac
import hashlib
import logging

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.auth import User
from routes.pop_helpers import RESEND_WEBHOOK_SECRET, TWILIO_AUTH_TOKEN
from routes.pop_notify import send_pop_onboarding_sms
from routes.pop_processor import process_pop_message
from routes.pop_list import list_router
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
router.include_router(wallet_router)
router.include_router(chat_router)
router.include_router(referral_router)
router.include_router(swaps_router)



@router.get("/health")
async def pop_health():
    """Health check for Pop/Bob service."""
    return {"status": "ok", "service": "pop"}

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

    # Resend inbound webhook payload structure
    sender = payload.get("from", "")
    # "from" may be a full address like "John <john@example.com>" — extract email
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]

    body = payload.get("text", "") or payload.get("html", "")
    subject = payload.get("subject", "")

    if not sender or not body:
        raise HTTPException(status_code=400, detail="Missing sender or body")

    logger.info(f"[Pop] Resend inbound from {sender}: {subject}")

    background_tasks.add_task(process_pop_message, sender, body, session, "email", None)

    return {"status": "accepted"}

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

    if not sender_phone or not body:
        raise HTTPException(status_code=400, detail="Missing From or Body")

    logger.info(f"[Pop] Twilio SMS from {sender_phone}: {body[:80]}")

    # Look up user by phone number
    statement = select(User).where(User.phone_number == sender_phone)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user and user.email:
        background_tasks.add_task(
            process_pop_message, user.email, body, session, "sms", sender_phone,
        )
    else:
        logger.info(f"[Pop] Unknown phone {sender_phone}. Sending onboarding SMS.")
        send_pop_onboarding_sms(sender_phone)

    # Return empty TwiML so Twilio doesn't retry
    return PlainTextResponse(
        content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
        media_type="application/xml",
    )