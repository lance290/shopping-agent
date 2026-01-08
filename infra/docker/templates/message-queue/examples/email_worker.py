"""
Example: Email Worker
Consumes email tasks from queue and sends them asynchronously
"""
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to: str, subject: str, body: str):
    """
    Send email via SMTP
    Configure with environment variables:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASS
    """
    import os
    
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.send_message(msg)
    
    print(f"✓ Email sent to {to}")

def process_email_task(payload: dict):
    """Process email task from queue"""
    try:
        send_email(
            to=payload["to"],
            subject=payload["subject"],
            body=payload["body"]
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# To use: Modify worker.py to call process_email_task() instead of process_message()
