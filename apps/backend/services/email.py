"""
Email service for outreach and handoff emails.
Uses Resend for transactional email delivery.
"""
import os
from typing import Optional
from dataclasses import dataclass

try:
    import resend
except ModuleNotFoundError:  # pragma: no cover
    resend = None  # type: ignore


@dataclass
class EmailResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# Check if Resend is available
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if RESEND_API_KEY and resend is not None:
    resend.api_key = RESEND_API_KEY

FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@buyanything.ai")
FROM_NAME = os.getenv("FROM_NAME", "BuyAnything")
ADMIN_EMAIL = os.getenv("ADMIN_NOTIFY_EMAIL", "")

# Dev mode: redirect ALL vendor-facing emails to this address instead
# Set to "" or unset in production to send to real vendors
# Safety: auto-disable in production even if accidentally set
_is_production = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production")
DEV_EMAIL_OVERRIDE = "" if _is_production else os.getenv("DEV_EMAIL_OVERRIDE", "")
if DEV_EMAIL_OVERRIDE:
    print(f"[EMAIL] DEV_EMAIL_OVERRIDE active — all emails redirect to {DEV_EMAIL_OVERRIDE}")
elif os.getenv("DEV_EMAIL_OVERRIDE"):
    print("[EMAIL] DEV_EMAIL_OVERRIDE ignored in production — emails go to real recipients")

# Base URL for magic links
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3003")


def _maybe_intercept(to_email: str, subject: str) -> tuple[str, str]:
    """In dev mode, redirect email to DEV_EMAIL_OVERRIDE and tag the subject."""
    if DEV_EMAIL_OVERRIDE:
        tagged_subject = f"[DEV → {to_email}] {subject}"
        return DEV_EMAIL_OVERRIDE, tagged_subject
    return to_email, subject


def get_quote_url(token: str) -> str:
    """Generate quote form URL from token."""
    return f"{APP_BASE_URL}/quote/{token}"


def get_tracking_pixel_url(token: str) -> str:
    """Generate tracking pixel URL."""
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return f"{backend_url}/outreach/track/open/{token}"


async def send_outreach_email(
    to_email: str,
    to_name: str,
    company_name: str,
    request_summary: str,
    choice_factors: list,
    quote_token: str,
) -> EmailResult:
    """
    Send RFP outreach email to a vendor.
    """
    quote_url = get_quote_url(quote_token)
    tracking_url = get_tracking_pixel_url(quote_token)
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    # Build choice factors HTML
    factors_html = ""
    if choice_factors:
        factors_html = "<ul>"
        for factor in choice_factors:
            factors_html += f"<li><strong>{factor.get('label', factor.get('name', ''))}:</strong> {factor.get('value', 'TBD')}</li>"
        factors_html += "</ul>"
    
    subject = f"RFP: {request_summary}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>New Request for Quote</h2>
        
        <p>Hi {to_name or 'there'},</p>
        
        <p>A buyer on BuyAnything is looking for a quote:</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📋 Request Summary</h3>
            <p><strong>{request_summary}</strong></p>
            {factors_html if factors_html else ''}
        </div>
        
        <p>To submit your quote, click the button below:</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{quote_url}" 
               style="background: #2563eb; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Submit Your Quote
            </a>
        </p>
        
        <p style="color: #666; font-size: 14px;">
            This link expires in 7 days. If you're not interested, no action is needed.
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #999; font-size: 12px;">
            You received this because {company_name} was identified as a potential provider.
            <br>
            <a href="{backend_url}/outreach/unsubscribe/{quote_token}" style="color: #999;">Unsubscribe</a> from future requests.
        </p>
        
        <p style="color: #bbb; font-size: 10px; margin-top: 20px;">
            BuyAnything.ai is a marketplace platform. We may earn a referral fee or commission when transactions are completed through our platform.
        </p>
        
        <img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">
    </body>
    </html>
    """
    
    text_content = f"""
    New Request for Quote
    
    Hi {to_name or 'there'},
    
    A buyer on BuyAnything is looking for a quote:
    
    Request: {request_summary}
    
    To submit your quote, visit:
    {quote_url}
    
    This link expires in 7 days.
    
    --
    BuyAnything Team
    
    Disclosure: BuyAnything.ai may earn a referral fee or commission on transactions completed through our platform.
    """
    
    # If Resend is configured, send real email
    to_email, subject = _maybe_intercept(to_email, subject)
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            }
            
            response = resend.Emails.send(params)
            
            return EmailResult(
                success=True,
                message_id=response.get("id"),
            )
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))
    
    # Demo mode: log email instead
    print(f"[DEMO EMAIL] To: {to_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    print(f"[DEMO EMAIL] Quote URL: {quote_url}")
    
    return EmailResult(success=True, message_id="demo-" + quote_token[:8])


async def send_custom_outreach_email(
    to_email: str,
    vendor_company: str,
    subject: str,
    body_text: str,
    quote_token: str,
    reply_to_email: str,
    sender_name: str = "BuyAnything",
) -> EmailResult:
    """
    Send a custom outreach email via Resend with reply-to set to the user's email.

    The email is sent FROM our domain (deliverability) but REPLY-TO goes to the user.
    Includes: quote link, tracking pixel, unsubscribe, affiliate disclosure.
    """
    quote_url = get_quote_url(quote_token)
    tracking_url = get_tracking_pixel_url(quote_token)
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    # Convert plain text body to HTML paragraphs
    body_html = body_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body_html = "<br>\n".join(body_html.split("\n"))

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="white-space: pre-wrap; line-height: 1.6;">
{body_html}
        </div>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{quote_url}"
               style="background: #2563eb; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Submit Your Quote
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #999; font-size: 12px;">
            Sent on behalf of {sender_name} via BuyAnything
            <br>
            <a href="{backend_url}/outreach/unsubscribe/{quote_token}" style="color: #999;">Unsubscribe</a>
        </p>

        <p style="color: #bbb; font-size: 10px;">
            BuyAnything.ai is a marketplace platform. We may earn a referral fee or commission
            when transactions are completed through our platform.
        </p>

        <img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">
    </body>
    </html>
    """

    plain_text = f"""{body_text}

---
Submit your quote: {quote_url}

Sent on behalf of {sender_name} via BuyAnything
Disclosure: BuyAnything.ai may earn a referral fee or commission on transactions.
"""

    to_email, subject = _maybe_intercept(to_email, subject)
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "reply_to": reply_to_email,
                "subject": subject,
                "html": html_content,
                "text": plain_text,
            }

            response = resend.Emails.send(params)

            return EmailResult(
                success=True,
                message_id=response.get("id"),
            )
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))

    # Demo mode
    print(f"[DEMO EMAIL] To: {to_email}")
    print(f"[DEMO EMAIL] Reply-To: {reply_to_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    print(f"[DEMO EMAIL] Quote URL: {quote_url}")

    return EmailResult(success=True, message_id="demo-custom-" + quote_token[:8])


async def send_reminder_email(
    to_email: str,
    to_name: str,
    company_name: str,
    request_summary: str,
    quote_token: str,
) -> EmailResult:
    """
    Send a 48h reminder email to a vendor who hasn't responded.
    """
    quote_url = get_quote_url(quote_token)
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    subject = f"Reminder: RFP for {request_summary}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Friendly Reminder</h2>
        
        <p>Hi {to_name or 'there'},</p>
        
        <p>We sent you a request for quote 2 days ago and haven't heard back yet.</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📋 Request Summary</h3>
            <p><strong>{request_summary}</strong></p>
        </div>
        
        <p>If you're interested, you can still submit your quote:</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{quote_url}" 
               style="background: #2563eb; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Submit Your Quote
            </a>
        </p>
        
        <p style="color: #666; font-size: 14px;">
            No worries if this isn't a fit — no action needed.
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #999; font-size: 12px;">
            <a href="{backend_url}/outreach/unsubscribe/{quote_token}" style="color: #999;">Unsubscribe</a> from future requests.
        </p>
        
        <p style="color: #bbb; font-size: 10px; margin-top: 20px;">
            BuyAnything.ai is a marketplace platform. We may earn a referral fee or commission when transactions are completed through our platform.
        </p>
    </body>
    </html>
    """
    
    to_email, subject = _maybe_intercept(to_email, subject)
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            response = resend.Emails.send(params)
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))
    
    print(f"[DEMO EMAIL] Reminder to: {to_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    return EmailResult(success=True, message_id="demo-reminder-" + quote_token[:8])


# Re-export handoff/merchant/triage/admin emails from extracted module
# so existing imports like `from services.email import send_handoff_buyer_email` keep working
from services.email_handoff import (  # noqa: F401
    send_handoff_buyer_email,
    send_handoff_seller_email,
    send_vendor_selected_email,
    send_triage_notification_email,
    send_merchant_verification_email,
    send_merchant_status_email,
    send_admin_vendor_alert,
)
