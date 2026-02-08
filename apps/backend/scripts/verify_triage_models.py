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

async def verify_models():
    print(f"Verifying models at {DATABASE_URL}")

    # Prevent running in production
    if os.getenv("RAILWAY_ENVIRONMENT") == "production":
        print("❌ ERROR: This script cannot be run in production environment.")
        print("   This script creates test data that could leak into the database.")
        sys.exit(1)

    # Warn about non-local environments
    if os.getenv("RAILWAY_ENVIRONMENT") or "railway.app" in DATABASE_URL:
        response = input("⚠️  WARNING: You're about to run this in a non-local environment.\n   Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

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

    bug = None
    try:
        async with async_session() as session:
            # Create a test bug report with new fields
            # Using a unique marker to identify test data
            bug = BugReport(
                notes="[TEST DATA] Verification Test Bug - DO NOT CREATE GITHUB ISSUE",
                classification="bug",
                classification_confidence=0.95,
                status="captured"
            )
            session.add(bug)
            await session.commit()
            await session.refresh(bug)

            print(f"Created test bug report {bug.id}")

            # Read it back
            stmt = select(BugReport).where(BugReport.id == bug.id)
            result = await session.exec(stmt)
            fetched_bug = result.first()

            if fetched_bug:
                print(f"Fetched bug: {fetched_bug.notes}")
                print(f"Classification: {fetched_bug.classification}")
                print(f"Confidence: {fetched_bug.classification_confidence}")

                if fetched_bug.classification == "bug" and fetched_bug.classification_confidence == 0.95:
                    print("✅ Verification SUCCESS: Fields are persisted correctly.")
                else:
                    print("❌ Verification FAILED: Fields mismatch.")
            else:
                print("❌ Verification FAILED: Could not fetch bug.")

            # Cleanup
            await session.delete(bug)
            await session.commit()
            print("Test data cleaned up.")
    except Exception as e:
        print(f"❌ ERROR during verification: {e}")
        if bug:
            print(f"⚠️  WARNING: Test bug report {bug.id} may not have been cleaned up.")
            print(f"   Run cleanup manually if needed.")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_models())
