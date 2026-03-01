import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

# Monkeypatch pgvector away so we don't need it for basic query tests
import sys
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

from apps.backend.database import engine
from apps.backend.models.rows import Row, Project
from apps.backend.models.auth import User
from apps.backend.routes.chat import _create_row

async def main():
    async with AsyncSession(engine) as session:
        # Create a user
        user = User(email="test@test.com", password_hash="hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create a test project
        project = Project(title="Test Project", user_id=user.id)
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Create a test row
        row = await _create_row(
            session, user.id, "test item", project.id,
            False, None, {}, "test item deals",
            desire_tier="commodity",
        )
        print(f"Created row ID: {row.id}, project_id: {row.project_id}, status: {row.status}")

        # Query the rows
        list_stmt = (
            select(Row)
            .where(Row.project_id == project.id)
            .where(Row.status.in_(["sourcing", "active", "pending"]))
            .order_by(Row.created_at.asc())
            .limit(20)
        )
        list_result = await session.execute(list_stmt)
        list_rows = list_result.scalars().all()
        print(f"Found {len(list_rows)} rows: {[r.id for r in list_rows]}")

asyncio.run(main())
