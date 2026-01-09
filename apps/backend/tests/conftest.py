import pytest
import sys
import os
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, init_db
from main import app, get_session

@pytest_asyncio.fixture(name="session")
async def session_fixture():
    await init_db()
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
