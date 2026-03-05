"""Tests for bugs.py — GitHub issue label logic and diagnostics serialization.

Covers:
- Bug reports get ["ai-fix"] label
- Feature requests get ["feature-request"] label (no ai-fix)
- Diagnostics parsed safely from dict or string before embedding in issue body
- Invalid/null diagnostics don't crash issue creation
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlmodel.ext.asyncio.session import AsyncSession

from models import BugReport, User
from routes.bugs import create_github_issue_task


async def _mock_get_session(session):
    yield session


class TestGitHubIssueLabels:

    @pytest.mark.asyncio
    async def test_bug_report_gets_ai_fix_label(self, session: AsyncSession, test_user: User):
        """Regular bug reports should get the 'ai-fix' label."""
        bug = BugReport(
            notes="Button doesn't work",
            severity="medium",
            category="ui",
            user_id=test_user.id,
            status="captured",
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={
            "type": "bug",
            "confidence": 0.95,
            "reasoning": "clear bug",
        })
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/1"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            await create_github_issue_task(bug.id)

        call_args = mock_github.create_issue.call_args
        labels = call_args.kwargs["labels"]
        assert "ai-fix" in labels
        assert "feature-request" not in labels

    @pytest.mark.asyncio
    async def test_feature_request_gets_feature_request_label(self, session: AsyncSession, test_user: User):
        """Feature requests should get 'feature-request' label without 'ai-fix'."""
        bug = BugReport(
            notes="It would be great if you could add dark mode",
            severity="low",
            category="feature",
            user_id=test_user.id,
            status="captured",
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={
            "type": "feature_request",
            "confidence": 0.9,
            "reasoning": "user wants dark mode",
        })
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/2"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            await create_github_issue_task(bug.id)

        call_args = mock_github.create_issue.call_args
        labels = call_args.kwargs["labels"]
        assert "feature-request" in labels
        assert "ai-fix" not in labels

        # Status ends as "sent" because issue creation succeeds (overrides feature_request)
        await session.refresh(bug)
        assert bug.status == "sent"


class TestGitHubIssueDiagnostics:

    @pytest.mark.asyncio
    async def test_dict_diagnostics_serialized_in_body(self, session: AsyncSession, test_user: User):
        """When diagnostics is a dict (from JSONB), it should be JSON-serialized in issue body."""
        diag_dict = {
            "url": "https://dev.buy-anything.com",
            "userAgent": "Mozilla/5.0",
            "logs": [],
            "network": [],
        }
        bug = BugReport(
            notes="Page crashes",
            severity="high",
            category="crash",
            user_id=test_user.id,
            status="captured",
            diagnostics=json.dumps(diag_dict),  # stored as JSON string, auto-deserialized by JSONB
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={"type": "bug", "confidence": 0.9, "reasoning": "crash"})
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/3"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            await create_github_issue_task(bug.id)

        call_args = mock_github.create_issue.call_args
        body = call_args.kwargs["body"]
        assert "### Diagnostics Summary" in body
        assert "Full Diagnostics JSON" in body
        assert "https://dev.buy-anything.com" in body

    @pytest.mark.asyncio
    async def test_null_diagnostics_omitted_from_body(self, session: AsyncSession, test_user: User):
        """When diagnostics is None, diagnostics sections should not appear in issue body."""
        bug = BugReport(
            notes="Something broke",
            severity="low",
            category="ui",
            user_id=test_user.id,
            status="captured",
            diagnostics=None,
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={"type": "bug", "confidence": 0.8, "reasoning": "bug"})
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/4"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            await create_github_issue_task(bug.id)

        call_args = mock_github.create_issue.call_args
        body = call_args.kwargs["body"]
        assert "### Diagnostics Summary" not in body
        assert "Full Diagnostics JSON" not in body

    @pytest.mark.asyncio
    async def test_null_string_diagnostics_omitted_from_body(self, session: AsyncSession, test_user: User):
        """When diagnostics is the JSON string 'null', diagnostics sections should not appear."""
        bug = BugReport(
            notes="Another issue",
            severity="low",
            category="ui",
            user_id=test_user.id,
            status="captured",
            diagnostics="null",
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={"type": "bug", "confidence": 0.7, "reasoning": "bug"})
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/5"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            await create_github_issue_task(bug.id)

        call_args = mock_github.create_issue.call_args
        body = call_args.kwargs["body"]
        assert "### Diagnostics Summary" not in body
        assert "Full Diagnostics JSON" not in body

    @pytest.mark.asyncio
    async def test_invalid_json_diagnostics_does_not_crash(self, session: AsyncSession, test_user: User):
        """When diagnostics is invalid JSON, issue creation should still succeed."""
        bug = BugReport(
            notes="Bug with bad diag",
            severity="medium",
            category="ui",
            user_id=test_user.id,
            status="captured",
            diagnostics="not valid json {{{",
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)

        mock_classify = AsyncMock(return_value={"type": "bug", "confidence": 0.8, "reasoning": "bug"})
        mock_github = AsyncMock()
        mock_github.create_issue.return_value = {"html_url": "https://github.com/test/issues/6"}
        mock_email = AsyncMock()

        with patch("routes.bugs.classify_report", mock_classify), \
             patch("routes.bugs.github_client", mock_github), \
             patch("routes.bugs.send_triage_notification_email", mock_email), \
             patch("routes.bugs.get_session", return_value=_mock_get_session(session)):
            # Should not raise
            await create_github_issue_task(bug.id)

        # Issue should still be created
        mock_github.create_issue.assert_called_once()
