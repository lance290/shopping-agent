"""Pop notification helpers: email and SMS senders."""

import logging

from services.email import EmailResult, RESEND_API_KEY, _maybe_intercept
from routes.pop_helpers import POP_FROM_EMAIL, POP_DOMAIN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

try:
    import resend
except ModuleNotFoundError:  # pragma: no cover
    resend = None  # type: ignore

try:
    from twilio.rest import Client as TwilioClient
except ModuleNotFoundError:  # pragma: no cover
    TwilioClient = None  # type: ignore

logger = logging.getLogger(__name__)


async def send_pop_reply(
    to_email: str,
    subject: str,
    body_text: str,
) -> EmailResult:
    """Send a reply email from Pop using the Resend service."""
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="white-space: pre-wrap; line-height: 1.6;">
{body_text.replace(chr(10), '<br>')}
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">Pop — your AI grocery savings assistant. Powered by BuyAnything.</p>
    </body>
    </html>
    """

    to_email, subject = _maybe_intercept(to_email, subject)
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"Pop <{POP_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": body_text,
            }
            response = resend.Emails.send(params)
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            logger.error(f"[Pop RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))

    logger.info(f"[Pop DEMO EMAIL] To: {to_email} | Subject: {subject}")
    return EmailResult(success=True, message_id="demo-pop-reply")


def send_pop_sms(to_phone: str, body_text: str) -> bool:
    """Send an outbound SMS from Pop via Twilio. Returns True on success."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        logger.info(f"[Pop DEMO SMS] To: {to_phone} | Body: {body_text[:120]}")
        return True
    if TwilioClient is None:
        logger.warning("[Pop] twilio package not installed — cannot send SMS")
        return False
    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=body_text[:1600],
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone,
        )
        logger.info(f"[Pop] SMS sent to {to_phone} (sid={msg.sid})")
        return True
    except Exception as e:
        logger.error(f"[Pop SMS ERROR] {e}")
        return False


async def send_pop_onboarding_email(email: str) -> EmailResult:
    """Send onboarding / welcome email to a new user who emailed Pop."""
    subject = "Welcome to Pop — your AI grocery savings assistant!"
    body_text = (
        "Hi there!\n\n"
        "I'm Pop, your AI grocery savings assistant.\n\n"
        "It looks like you don't have an account yet. "
        "To get started, visit:\n\n"
        f"  {POP_DOMAIN}/signup\n\n"
        "Once you're signed up, just email me your shopping list "
        "and I'll find the best deals for you!\n\n"
        "— Pop"
    )
    return await send_pop_reply(email, subject, body_text)


def send_pop_onboarding_sms(phone: str) -> bool:
    """Send onboarding SMS to an unknown phone number."""
    body = (
        f"Hi! I'm Pop, your AI grocery savings assistant. "
        f"To get started, sign up at {POP_DOMAIN} "
        f"and add your phone number to your profile. "
        f"Then text me your shopping list!"
    )
    return send_pop_sms(phone, body)
