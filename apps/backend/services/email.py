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

# Base URL for magic links
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3003")


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


async def send_handoff_buyer_email(
    buyer_email: str,
    buyer_name: Optional[str],
    seller_name: str,
    seller_company: str,
    seller_email: str,
    seller_phone: Optional[str],
    request_summary: str,
    quote_price: float,
    quote_description: str,
) -> EmailResult:
    """
    Send introduction email to buyer after selecting a quote.
    """
    subject = f"Your quote from {seller_company} for {request_summary}"
    
    phone_html = f"<li><strong>Phone:</strong> {seller_phone}</li>" if seller_phone else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>🎉 Great news!</h2>
        
        <p>Hi {buyer_name or 'there'},</p>
        
        <p>You've selected <strong>{seller_company}</strong> for your request.</p>
        
        <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #22c55e;">
            <h3 style="margin-top: 0;">📋 Quote Summary</h3>
            <p><strong>Price:</strong> ${quote_price:,.2f}</p>
            <p><strong>Details:</strong> {quote_description}</p>
        </div>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📞 Seller Contact</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>Company:</strong> {seller_company}</li>
                <li><strong>Contact:</strong> {seller_name}</li>
                <li><strong>Email:</strong> <a href="mailto:{seller_email}">{seller_email}</a></li>
                {phone_html}
            </ul>
        </div>
        
        <h3>Next Steps</h3>
        <ol>
            <li>Reach out to {seller_name} to finalize details</li>
            <li>Agree on timeline and payment terms</li>
            <li>Once complete, let us know how it went!</li>
        </ol>
        
        <p>Questions? Reply to this email.</p>
        
        <p>—BuyAnything Team</p>
    </body>
    </html>
    """
    
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [buyer_email],
                "subject": subject,
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            
            return EmailResult(
                success=True,
                message_id=response.get("id"),
            )
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))
    
    print(f"[DEMO EMAIL] Buyer handoff to: {buyer_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    return EmailResult(success=True, message_id="demo-buyer-handoff")


async def send_handoff_seller_email(
    seller_email: str,
    seller_name: Optional[str],
    seller_company: str,
    buyer_name: Optional[str],
    buyer_email: str,
    buyer_phone: Optional[str],
    request_summary: str,
    quote_price: float,
) -> EmailResult:
    """
    Send notification email to seller when their quote is accepted.
    """
    subject = f"🎉 Your quote was accepted! {request_summary}"
    
    phone_html = f"<li><strong>Phone:</strong> {buyer_phone}</li>" if buyer_phone else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>🎉 Congratulations!</h2>
        
        <p>Hi {seller_name or 'there'},</p>
        
        <p><strong>{buyer_name or 'A buyer'}</strong> has accepted your quote for:</p>
        
        <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #22c55e;">
            <h3 style="margin-top: 0;">📋 Deal Summary</h3>
            <p><strong>Request:</strong> {request_summary}</p>
            <p><strong>Your Quote:</strong> ${quote_price:,.2f}</p>
        </div>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📞 Buyer Contact</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>Name:</strong> {buyer_name or 'Not provided'}</li>
                <li><strong>Email:</strong> <a href="mailto:{buyer_email}">{buyer_email}</a></li>
                {phone_html}
            </ul>
        </div>
        
        <h3>Next Steps</h3>
        <p>Reach out to the buyer within 24 hours to finalize the deal.</p>
        
        <p>Congrats on winning this opportunity!</p>
        
        <p>—BuyAnything Team</p>
    </body>
    </html>
    """
    
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [seller_email],
                "subject": subject,
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            
            return EmailResult(
                success=True,
                message_id=response.get("id"),
            )
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))
    
    print(f"[DEMO EMAIL] Seller notification to: {seller_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    return EmailResult(success=True, message_id="demo-seller-handoff")


async def send_triage_notification_email(
    report_id: int,
    classification: str,
    confidence: float,
    notes: str,
    user_id: Optional[int],
    page_url: Optional[str],
    screenshot_url: Optional[str] = None,
    reasoning: str = ""
) -> EmailResult:
    """
    Send notification email to admin for feature requests or low-confidence triage.
    """
    admin_email = "masseyl@gmail.com"  # Hardcoded for MVP
    
    subject = f"[{classification.upper()}] Triage Report #{report_id} ({confidence:.2f})"
    if confidence < 0.7:  # Visual indicator for low confidence
        subject = f"⚠️ [LOW CONFIDENCE] {subject}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Bug Report Triage</h2>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📊 Classification</h3>
            <p><strong>Type:</strong> {classification}</p>
            <p><strong>Confidence:</strong> {confidence:.2f}</p>
            <p><strong>Reasoning:</strong> {reasoning}</p>
        </div>

        <div style="background: #fff; border: 1px solid #eee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">📝 User Report</h3>
            <p><strong>Notes:</strong> {notes}</p>
            <p><strong>User ID:</strong> {user_id or 'Anonymous'}</p>
            <p><strong>Page URL:</strong> {page_url or 'N/A'}</p>
        </div>
        
        {f'<p><a href="{screenshot_url}">View Screenshot</a></p>' if screenshot_url else ''}
        
        <p style="color: #666; font-size: 12px;">
            Report ID: {report_id}
        </p>
    </body>
    </html>
    """
    
    text_content = f"""
    Bug Report Triage
    
    Classification: {classification} ({confidence:.2f})
    Reasoning: {reasoning}
    
    User Report:
    Notes: {notes}
    User ID: {user_id or 'Anonymous'}
    Page URL: {page_url or 'N/A'}
    
    Screenshot: {screenshot_url or 'N/A'}
    Report ID: {report_id}
    """

    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [admin_email],
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
    
    print(f"[DEMO EMAIL] Triage notification to: {admin_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    return EmailResult(success=True, message_id="demo-triage")


async def send_merchant_verification_email(
    to_email: str,
    to_name: str,
    verification_token: str,
) -> EmailResult:
    """
    Send verification email to a new merchant.
    """
    verification_url = f"{APP_BASE_URL}/merchants/verify-email?token={verification_token}"
    
    subject = "Verify your email to complete your seller registration"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Welcome to BuyAnything!</h2>
        
        <p>Hi {to_name or 'there'},</p>
        
        <p>Thanks for registering as a seller. To activate your account and start receiving quote requests, please verify your email address.</p>
        
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" 
               style="background: #2563eb; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Verify Email
            </a>
        </p>
        
        <p style="color: #666; font-size: 14px;">
            This link expires in 72 hours.
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #999; font-size: 12px;">
            If you didn't create an account, you can safely ignore this email.
        </p>
    </body>
    </html>
    """
    
    text_content = f"""
    Welcome to BuyAnything!
    
    Hi {to_name or 'there'},
    
    Thanks for registering as a seller. To activate your account, please verify your email address:
    
    {verification_url}
    
    This link expires in 72 hours.
    
    If you didn't create an account, you can safely ignore this email.
    """
    
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
    
    print(f"[DEMO EMAIL] Merchant verification to: {to_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    print(f"[DEMO EMAIL] URL: {verification_url}")
    return EmailResult(success=True, message_id="demo-merchant-verification")


async def send_merchant_status_email(
    to_email: str,
    to_name: str,
    status_type: str,  # "approved", "rejected", "suspended", "unsuspended"
    reason: Optional[str] = None,
) -> EmailResult:
    """
    Send notification to merchant about account status change.
    """
    subject_map = {
        "approved": "🎉 Your business has been verified!",
        "rejected": "Update on your seller application",
        "suspended": "⚠️ Important: Your seller account has been suspended",
        "unsuspended": "Your seller account has been restored",
    }
    
    subject = subject_map.get(status_type, "Account Status Update")
    
    # Content variations
    if status_type == "approved":
        body_html = f"""
        <p>Great news! Your business profile has been verified by our team.</p>
        <p>Your quotes will now display a <strong>Verified Business</strong> badge to buyers, increasing trust and visibility.</p>
        <p>Keep up the good work!</p>
        """
    elif status_type == "rejected":
        body_html = f"""
        <p>We reviewed your business profile and were unable to verify it at this time.</p>
        <p><strong>Reason:</strong> {reason or 'Does not meet current marketplace criteria.'}</p>
        <p>You can update your profile and reply to this email to request a re-review.</p>
        """
    elif status_type == "suspended":
        body_html = f"""
        <p>Your seller account has been suspended effective immediately.</p>
        <p><strong>Reason:</strong> {reason or 'Violation of platform policies.'}</p>
        <p>While suspended, your quotes will not be visible to buyers.</p>
        <p>If you believe this is a mistake, please <a href="{APP_BASE_URL}/help/contact">contact support</a>.</p>
        """
    elif status_type == "unsuspended":
        body_html = f"""
        <p>Your account suspension has been lifted. Your previous verification status has been restored.</p>
        <p>You can now submit quotes and interact with buyers again.</p>
        """
    else:
        body_html = f"<p>Your account status has been updated to: <strong>{status_type}</strong>.</p>"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>{subject}</h2>
        
        <p>Hi {to_name or 'there'},</p>
        
        {body_html}
        
        <p>—BuyAnything Team</p>
    </body>
    </html>
    """
    
    body_text = body_html.replace('<p>', '').replace('</p>', '\n\n').replace('<strong>', '').replace('</strong>', '').replace('<a href="', '').replace('">contact support</a>', 'contact support')
    text_content = f"""
    {subject}
    
    Hi {to_name or 'there'},
    
    {body_text}
    
    —BuyAnything Team
    """
    
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
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            print(f"[RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))
    
    print(f"[DEMO EMAIL] Status update ({status_type}) to: {to_email}")
    print(f"[DEMO EMAIL] Subject: {subject}")
    return EmailResult(success=True, message_id=f"demo-status-{status_type}")


async def send_admin_vendor_alert(
    event_type: str,
    vendor_name: Optional[str] = None,
    vendor_email: Optional[str] = None,
    vendor_company: Optional[str] = None,
    row_title: Optional[str] = None,
    row_id: Optional[int] = None,
    quote_price: Optional[float] = None,
    quote_description: Optional[str] = None,
) -> EmailResult:
    """
    Send an email alert to the admin when a vendor engages with outreach.
    event_type: "opened", "clicked", "quote_submitted"
    """
    if not ADMIN_EMAIL:
        print(f"[ADMIN ALERT] No ADMIN_NOTIFY_EMAIL set — skipping {event_type} alert")
        return EmailResult(success=False, error="No admin email configured")

    vendor_display = vendor_company or vendor_name or vendor_email or "Unknown vendor"

    subjects = {
        "opened": f"📬 {vendor_display} opened your outreach email",
        "clicked": f"🔗 {vendor_display} clicked the quote link",
        "quote_submitted": f"💰 {vendor_display} submitted a quote!",
        "deal_selected": f"🤝 Deal selected: {vendor_display}",
    }
    subject = subjects.get(event_type, f"Vendor activity: {event_type}")

    emoji = {"opened": "📬", "clicked": "🔗", "quote_submitted": "💰", "deal_selected": "🤝"}.get(event_type, "📋")
    action = {
        "opened": "opened your outreach email",
        "clicked": "clicked the quote link",
        "quote_submitted": "submitted a quote",
        "deal_selected": "was selected by a buyer — deal in progress!",
    }.get(event_type, event_type)

    quote_html = ""
    if event_type == "quote_submitted" and quote_price is not None:
        quote_html = f"""
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <strong>Quote: ${quote_price:,.2f}</strong><br/>
            {quote_description or "No description provided"}
        </div>
        """
    elif event_type == "deal_selected" and quote_price is not None:
        quote_html = f"""
        <div style="background: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 16px; margin: 16px 0;">
            <strong>Deal value: ${quote_price:,.2f}</strong>
        </div>
        """

    row_link = f"{APP_BASE_URL}" if not row_id else f"{APP_BASE_URL}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="font-size: 32px; margin-bottom: 8px;">{emoji}</div>
        <h2 style="margin: 0 0 4px 0; color: #111;">{vendor_display}</h2>
        <p style="margin: 0 0 16px 0; color: #666;">{action}</p>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
            <tr><td style="padding: 6px 0; color: #888; width: 100px;">Request</td><td style="padding: 6px 0;"><strong>{row_title or "Unknown"}</strong></td></tr>
            <tr><td style="padding: 6px 0; color: #888;">Vendor</td><td style="padding: 6px 0;">{vendor_display}</td></tr>
            <tr><td style="padding: 6px 0; color: #888;">Email</td><td style="padding: 6px 0;">{vendor_email or "N/A"}</td></tr>
        </table>
        {quote_html}
        <p style="font-size: 12px; color: #999;">BuyAnything Vendor Activity Alert</p>
    </div>
    """

    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [ADMIN_EMAIL],
                "subject": subject,
                "html": html,
            }
            response = resend.Emails.send(params)
            print(f"[ADMIN ALERT] Sent {event_type} alert for {vendor_display}")
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            print(f"[ADMIN ALERT ERROR] {e}")
            return EmailResult(success=False, error=str(e))

    print(f"[ADMIN ALERT] {event_type}: {vendor_display} — {row_title}")
    return EmailResult(success=True, message_id=f"demo-admin-{event_type}")
