import os
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from models import BugReport

# Configuration
NOTIFICATION_SLACK_WEBHOOK = os.getenv("NOTIFICATION_SLACK_WEBHOOK")
NOTIFICATION_EMAIL_TARGET = os.getenv("NOTIFICATION_EMAIL_TARGET") # e.g. "team@example.com"

# Routing Policy
SEVERITY_LEVELS = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "blocking": 3
}

NOTIFY_THRESHOLD = SEVERITY_LEVELS.get(os.getenv("NOTIFICATION_THRESHOLD", "high"), 2)

logger = logging.getLogger("notifications")

def should_notify(bug: BugReport) -> bool:
    """
    Determine if a bug report requires immediate internal notification.
    Policy: Severity >= High OR Category = 'security' (if we had it, or maybe 'auth' + high?)
    """
    severity_val = SEVERITY_LEVELS.get(bug.severity.lower(), 0)
    
    # Always notify on blocking
    if bug.severity.lower() == "blocking":
        return True
        
    # Notify if meets threshold
    if severity_val >= NOTIFY_THRESHOLD:
        return True
        
    return False

# Rate Limiting for Notifications
_notification_history = []
MAX_NOTIFICATIONS_PER_HOUR = 10

def check_rate_limit() -> bool:
    global _notification_history
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=1)
    
    # Prune old history
    _notification_history = [t for t in _notification_history if t > cutoff]
    
    if len(_notification_history) >= MAX_NOTIFICATIONS_PER_HOUR:
        logger.warning("[NOTIFICATIONS] Rate limit exceeded. Suppressing notification.")
        return False
        
    _notification_history.append(now)
    return True

async def send_internal_notification(bug: BugReport):
    """
    Send internal notification (Slack/Email/Log) for high-priority bugs.
    Payload is link-only (no sensitive data).
    """
    if not should_notify(bug):
        return

    if not check_rate_limit():
        return

    message = f"🚨 **{bug.severity.upper()}** Bug Reported!\n"
    message += f"Category: {bug.category}\n"
    message += f"Note: {bug.notes[:100]}...\n"
    message += f"Report ID: {bug.id}\n"
    
    # Links
    if bug.github_issue_url:
        message += f"Issue: {bug.github_issue_url}\n"
    
    # Ideally we have a frontend URL for the status page
    # frontend_url = f"{FRONTEND_BASE_URL}/bugs/{bug.id}"
    # message += f"Status: {frontend_url}\n"

    logger.info(f"[NOTIFICATIONS] Triggering notification for Bug {bug.id} ({bug.severity})")

    # 1. Slack Webhook (if configured)
    if NOTIFICATION_SLACK_WEBHOOK:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    NOTIFICATION_SLACK_WEBHOOK,
                    json={"text": message}
                )
                logger.info(f"[NOTIFICATIONS] Sent Slack notification for Bug {bug.id}")
        except Exception as e:
            logger.error(f"[NOTIFICATIONS] Failed to send Slack webhook: {e}")

    # 2. Email (via Resend if configured)
    # This recycles the existing Resend setup from main.py if we were to import it, 
    # but for now we'll just log if configured to keep this module decoupled or simple.
    if NOTIFICATION_EMAIL_TARGET:
        # Placeholder for email logic
        logger.info(f"[NOTIFICATIONS] Would send email to {NOTIFICATION_EMAIL_TARGET}: {message}")
    
    # 3. Log (always)
    print(f"!!! INTERNAL NOTIFICATION !!!\n{message}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
