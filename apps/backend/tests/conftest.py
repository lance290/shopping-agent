import pytest
import sys
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, init_db
from main import app, get_session

@pytest_asyncio.fixture(name="session", scope="function")
async def session_fixture():
    # Use NullPool for tests to avoid asyncpg InterfaceError: cannot perform operation: another operation is in progress
    # This ensures each test gets a fresh connection that is closed at the end
    # Pass the URL object directly to avoid password masking in string representation
    
    test_engine = create_async_engine(
        engine.url, 
        echo=False, 
        future=True, 
        poolclass=NullPool
    )
    
    # Re-init DB on the test engine to ensure schema
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    
    await test_engine.dispose()

@pytest_asyncio.fixture(name="test_user")
async def test_user_fixture(session: AsyncSession):
    """Create a test user for authentication tests."""
    from models import User

    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="auth_user_and_token")
async def auth_user_and_token_fixture(session: AsyncSession):
    """Create authenticated user and return (user, token) tuple."""
    from models import User, AuthSession, hash_token, generate_session_token

    user = User(email="testauth@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    return user, token


@pytest_asyncio.fixture(name="test_bid")
async def test_bid_fixture(session: AsyncSession, auth_user_and_token):
    """Create test bid for like/comment/share tests."""
    from models import Row, Bid

    user, _ = auth_user_and_token

    row = Row(title="Test Row", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        item_url="https://example.com/product"
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    return bid


@pytest_asyncio.fixture(name="test_row")
async def test_row_fixture(session: AsyncSession, auth_user_and_token):
    """Create test row for share tests."""
    from models import Row

    user, _ = auth_user_and_token

    row = Row(title="Shareable Row", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return row


@pytest_asyncio.fixture(name="test_project")
async def test_project_fixture(session: AsyncSession, auth_user_and_token):
    """Create test project for share tests."""
    from models import Project

    user, _ = auth_user_and_token

    project = Project(title="Shareable Project", user_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    return project
