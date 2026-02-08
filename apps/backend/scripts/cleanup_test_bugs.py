"""
Cleanup script to remove test bug reports that leaked into the database.

This script identifies and removes bug reports that were created by test/verification
scripts and should not be in the database.
"""
import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import models/database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DATABASE_URL
from models import BugReport

async def cleanup_test_bugs():
    """Remove test bug reports from the database."""
    print(f"Connecting to {DATABASE_URL}")

    # Configure connection args for production (Railway) if needed
    connect_args = {}
    if os.getenv("RAILWAY_ENVIRONMENT"):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    engine = create_async_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find test bug reports by known test patterns
        test_patterns = [
            "Verification Test Bug",
            "[TEST DATA]",
            "verification test"
        ]

        print("\nSearching for test bug reports...")
        test_bugs = []

        for pattern in test_patterns:
            stmt = select(BugReport).where(BugReport.notes.ilike(f"%{pattern}%"))
            result = await session.exec(stmt)
            bugs = result.all()
            test_bugs.extend(bugs)

        # Remove duplicates
        test_bugs = list({bug.id: bug for bug in test_bugs}.values())

        if not test_bugs:
            print("✅ No test bug reports found.")
            await engine.dispose()
            return

        print(f"\nFound {len(test_bugs)} test bug report(s):")
        for bug in test_bugs:
            print(f"  - Bug #{bug.id}: {bug.notes[:60]}...")
            print(f"    Status: {bug.status}, Created: {bug.created_at}")
            if bug.github_issue_url:
                print(f"    GitHub Issue: {bug.github_issue_url}")

        # Confirm deletion
        if os.getenv("RAILWAY_ENVIRONMENT") or not sys.stdin.isatty():
            # In non-interactive environment, require explicit flag
            if not os.getenv("CONFIRM_CLEANUP"):
                print("\n❌ Cleanup aborted: Set CONFIRM_CLEANUP=1 to proceed in non-interactive mode.")
                await engine.dispose()
                return
            response = "yes"
        else:
            response = input("\nDelete these test bug reports? (yes/no): ")

        if response.lower() != "yes":
            print("Cleanup aborted.")
            await engine.dispose()
            return

        # Delete test bugs
        deleted_count = 0
        for bug in test_bugs:
            await session.delete(bug)
            deleted_count += 1
            print(f"  Deleted bug #{bug.id}")

        await session.commit()
        print(f"\n✅ Successfully deleted {deleted_count} test bug report(s).")

        # Note about GitHub issues
        github_issues = [bug.github_issue_url for bug in test_bugs if bug.github_issue_url]
        if github_issues:
            print("\n⚠️  Note: The following GitHub issues were created for test bugs:")
            for url in github_issues:
                print(f"  - {url}")
            print("  These should be closed manually.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_test_bugs())
