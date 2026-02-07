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
