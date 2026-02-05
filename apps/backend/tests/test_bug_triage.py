import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models import BugReport
from routes.bugs import create_github_issue_task, TRIAGE_CONFIDENCE_THRESHOLD

# Helper to mock get_session async generator
async def mock_get_session_gen(session):
    yield session

@pytest.mark.asyncio
async def test_triage_high_confidence_bug(session, test_user):
    """
    Test that a high-confidence bug report creates a GitHub issue and does NOT send a triage email.
    """
    # Setup
    bug = BugReport(
        notes="App crashes when I click the button",
        expected="Button should work",
        actual="App crashed",
        user_id=test_user.id,
        status="captured"
    )
    session.add(bug)
    await session.commit()
    await session.refresh(bug)

    # Mocks
    mock_classify = AsyncMock(return_value={
        "type": "bug",
        "confidence": 0.95,
        "reasoning": "Clear bug description"
    })
    
    mock_github = AsyncMock()
    mock_github.create_issue.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
    
    mock_email = AsyncMock()

    # We must patch get_session to use the SAME session as the test
    # Otherwise create_github_issue_task uses a new session/transaction that might conflict or not see data
    with patch("routes.bugs.classify_report", mock_classify), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.send_triage_notification_email", mock_email), \
         patch("routes.bugs.get_session", return_value=mock_get_session_gen(session)):
        
        await create_github_issue_task(bug.id)
        
        # Verify DB updates
        await session.refresh(bug)
        assert bug.classification == "bug"
        assert bug.classification_confidence == 0.95
        assert bug.github_issue_url == "https://github.com/owner/repo/issues/1"
        assert bug.status == "sent"

        # Verify GitHub called
        mock_github.create_issue.assert_called_once()
        call_args = mock_github.create_issue.call_args
        assert "[Bug] App crashes when I click the button..." in call_args.kwargs['title']
        assert "### Triage" in call_args.kwargs['body']
        assert "**Classification**: bug" in call_args.kwargs['body']

        # Verify Email NOT called
        mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_triage_high_confidence_feature_request(session, test_user):
    """
    Test that a high-confidence feature request sends an email and does NOT create a GitHub issue.
    """
    # Setup
    bug = BugReport(
        notes="Please add dark mode",
        user_id=test_user.id,
        status="captured"
    )
    session.add(bug)
    await session.commit()
    await session.refresh(bug)

    # Mocks
    mock_classify = AsyncMock(return_value={
        "type": "feature_request",
        "confidence": 0.90,
        "reasoning": "User is asking for a new feature"
    })
    
    mock_github = AsyncMock()
    mock_email = AsyncMock()

    with patch("routes.bugs.classify_report", mock_classify), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.send_triage_notification_email", mock_email), \
         patch("routes.bugs.get_session", return_value=mock_get_session_gen(session)):
        
        await create_github_issue_task(bug.id)
        
        # Verify DB updates
        await session.refresh(bug)
        assert bug.classification == "feature_request"
        assert bug.classification_confidence == 0.90
        assert bug.github_issue_url is None
        assert bug.status == "feature_request"

        # Verify GitHub NOT called
        mock_github.create_issue.assert_not_called()

        # Verify Email called
        mock_email.assert_called_once()
        assert mock_email.call_args.kwargs['classification'] == "feature_request"


@pytest.mark.asyncio
async def test_triage_low_confidence_ambiguous(session, test_user):
    """
    Test that a low-confidence report (ambiguous) is treated as a bug (safety) BUT also sends an email.
    """
    # Setup
    bug = BugReport(
        notes="It feels weird when I do this",
        user_id=test_user.id,
        status="captured"
    )
    session.add(bug)
    await session.commit()
    await session.refresh(bug)

    # Mocks
    mock_classify = AsyncMock(return_value={
        "type": "feature_request", # Even if model thinks feature, low confidence overrides routing
        "confidence": 0.5, # Below 0.7 threshold
        "reasoning": "Unsure"
    })
    
    mock_github = AsyncMock()
    mock_github.create_issue.return_value = {"html_url": "https://github.com/owner/repo/issues/2"}
    
    mock_email = AsyncMock()

    with patch("routes.bugs.classify_report", mock_classify), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.send_triage_notification_email", mock_email), \
         patch("routes.bugs.get_session", return_value=mock_get_session_gen(session)):
        
        await create_github_issue_task(bug.id)
        
        # Verify DB updates
        await session.refresh(bug)
        assert bug.classification == "feature_request"
        assert bug.classification_confidence == 0.5
        assert bug.github_issue_url == "https://github.com/owner/repo/issues/2" # Should still create issue
        
        # Verify GitHub called (Safety fallback)
        mock_github.create_issue.assert_called_once()

        # Verify Email called (because confidence < threshold)
        mock_email.assert_called_once()
        assert mock_email.call_args.kwargs['confidence'] == 0.5
