import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import BugReport
from routes.bugs import create_github_issue_task, classify_report
from database import get_session

# Mock data
MOCK_BUG_ID = 9999
MOCK_USER_ID = 1

async def run_manual_verification():
    print("🚀 Starting Manual Verification of Triage Flow")
    
    # 1. Simulate a Feature Request
    print("\n--- Test Case 1: Feature Request ---")
    print("Simulating bug report: 'Please add dark mode'")
    
    # We need to mock the DB session and external calls since we don't want to write to real DB or call real APIs
    mock_session = AsyncMock()
    mock_bug = BugReport(
        id=MOCK_BUG_ID,
        notes="Please add dark mode",
        user_id=MOCK_USER_ID,
        status="captured",
        diagnostics=None
    )
    mock_session.get.return_value = mock_bug
    
    # Mock the get_session generator
    async def mock_get_session_gen():
        yield mock_session

    # Mock classifier to return feature request
    mock_classifier = AsyncMock(return_value={
        "type": "feature_request",
        "confidence": 0.95,
        "reasoning": "User wants new feature"
    })

    # Mock GitHub (should NOT be called)
    mock_github = AsyncMock()
    
    # Mock Email (SHOULD be called)
    mock_email = AsyncMock()

    with patch("routes.bugs.get_session", mock_get_session_gen), \
         patch("routes.bugs.classify_report", mock_classifier), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.send_triage_notification_email", mock_email):
        
        await create_github_issue_task(MOCK_BUG_ID)
        
        # Verify
        if mock_bug.status == "feature_request":
            print("✅ Status updated to 'feature_request'")
        else:
            print(f"❌ Status mismatch: {mock_bug.status}")
            
        if mock_github.create_issue.called:
            print("❌ GitHub issue created (unexpected)")
        else:
            print("✅ No GitHub issue created")
            
        if mock_email.called:
            print("✅ Triage email sent")
        else:
            print("❌ Triage email NOT sent")

    # 2. Simulate a Bug
    print("\n--- Test Case 2: Crash Bug ---")
    print("Simulating bug report: 'App crashes on load'")
    
    mock_bug.notes = "App crashes on load"
    mock_bug.status = "captured"
    mock_bug.github_issue_url = None # Reset
    
    mock_classifier.return_value = {
        "type": "bug",
        "confidence": 0.98,
        "reasoning": "Crash report"
    }
    
    mock_github.create_issue.return_value = {"html_url": "http://github.com/issue/1"}
    mock_email.reset_mock()

    with patch("routes.bugs.get_session", mock_get_session_gen), \
         patch("routes.bugs.classify_report", mock_classifier), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.send_triage_notification_email", mock_email):
        
        await create_github_issue_task(MOCK_BUG_ID)
        
        if mock_bug.status == "sent":
            print("✅ Status updated to 'sent'")
        else:
            print(f"❌ Status mismatch: {mock_bug.status}")
            
        if mock_github.create_issue.called:
            print("✅ GitHub issue created")
        else:
            print("❌ GitHub issue NOT created")
            
        if mock_email.called:
            print("❌ Triage email sent (unexpected)")
        else:
            print("✅ No triage email sent")

    print("\n✨ Manual Verification Complete")

if __name__ == "__main__":
    asyncio.run(run_manual_verification())
