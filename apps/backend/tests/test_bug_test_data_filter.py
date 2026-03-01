"""
Test to verify that test bug reports are filtered from GitHub issue creation.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models import BugReport
from routes.bugs import create_github_issue_task


@pytest.mark.asyncio
async def test_test_bug_filtered_from_github_issue_creation():
    """Test that bug reports with test markers don't create GitHub issues."""

    test_cases = [
        "[TEST DATA] Sample test bug",
        "Verification Test Bug",
        "Some bug DO NOT CREATE GITHUB ISSUE",
        "[test data] lowercase test marker",
        "VERIFICATION TEST BUG uppercase",
        "Test bug to verify GitHub token on Railway",
        "test bug to verify integration is working",
    ]

    for notes in test_cases:
        mock_session = AsyncMock()
        mock_bug = BugReport(
            id=9999,
            notes=notes,
            user_id=1,
            status="captured",
            github_issue_url=None,
            diagnostics=None
        )
        mock_session.get.return_value = mock_bug

        # Mock the get_session generator
        async def mock_get_session_gen():
            yield mock_session

        # Mock GitHub client
        mock_github = AsyncMock()

        with patch("routes.bugs.get_session", mock_get_session_gen), \
             patch("routes.bugs.github_client", mock_github):

            await create_github_issue_task(9999)

            # Verify GitHub issue was NOT created
            assert not mock_github.create_issue.called, f"GitHub issue should not be created for: {notes}"
            print(f"✅ Test passed: Filtered test bug with notes: {notes[:50]}")


@pytest.mark.asyncio
async def test_real_bug_creates_github_issue():
    """Test that real bug reports DO create GitHub issues."""

    mock_session = AsyncMock()
    mock_bug = BugReport(
        id=9999,
        notes="App crashes when clicking submit button",
        user_id=1,
        status="captured",
        github_issue_url=None,
        diagnostics=None,
        severity="high",
        category="ui",
        classification="bug",
        classification_confidence=0.95
    )
    mock_session.get.return_value = mock_bug
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    # Mock the get_session generator
    async def mock_get_session_gen():
        yield mock_session

    # Mock GitHub client to return a successful response
    mock_github = AsyncMock()
    mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issue/123"}

    # Mock the classify_report function
    mock_classify = AsyncMock(return_value={
        "type": "bug",
        "confidence": 0.95,
        "reasoning": "Crash report"
    })

    with patch("routes.bugs.get_session", mock_get_session_gen), \
         patch("routes.bugs.github_client", mock_github), \
         patch("routes.bugs.classify_report", mock_classify):

        await create_github_issue_task(9999)

        # Verify GitHub issue WAS created
        assert mock_github.create_issue.called, "GitHub issue should be created for real bugs"
        print("✅ Test passed: Real bug creates GitHub issue")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_test_bug_filtered_from_github_issue_creation())
    asyncio.run(test_real_bug_creates_github_issue())
    print("\n✅ All tests passed!")
