import pytest
import sys
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
import sqlalchemy
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, init_db
from main import app, get_session

# Disable CSRF protection in tests — test clients don't use browser cookies
from security.csrf import set_csrf_secret
set_csrf_secret(None)  # type: ignore[arg-type]

@pytest_asyncio.fixture(name="session", scope="function")
async def session_fixture():
    # Use a SEPARATE test database to avoid nuking dev data.
    # Derive test DB URL from the main engine URL by appending "_test".
    from urllib.parse import urlparse, urlunparse

    main_url = engine.url.render_as_string(hide_password=False)
    # If DATABASE_URL env var is set, use it directly (overrides default port)
    env_url = os.environ.get("DATABASE_URL", "")
    if env_url:
        main_url = env_url
    parsed = urlparse(main_url)

    # Replace DB name: /shopping_agent -> /shopping_agent_test
    test_path = parsed.path
    if "/shopping_agent" in test_path and "_test" not in test_path:
        test_path = test_path.replace("/shopping_agent", "/shopping_agent_test")
    test_url = urlunparse(parsed._replace(path=test_path))

    # Admin URL: swap DB name to /postgres (keep query params like ?ssl=disable)
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    admin_engine = create_async_engine(admin_url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                sqlalchemy.text("SELECT 1 FROM pg_database WHERE datname = 'shopping_agent_test'")
            )
            if not result.scalar():
                await conn.execute(sqlalchemy.text("CREATE DATABASE shopping_agent_test"))
    finally:
        await admin_engine.dispose()

    test_engine = create_async_engine(
        test_url,
        echo=False,
        future=True,
        poolclass=NullPool,
    )

    # Check pgvector availability in its own autocommit connection.
    # If unavailable, skip DB-dependent tests rather than failing with a schema error.
    autocommit_engine = create_async_engine(
        test_url, echo=False, future=True, poolclass=NullPool,
        execution_options={"isolation_level": "AUTOCOMMIT"},
    )
    async with autocommit_engine.connect() as conn:
        try:
            await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            await autocommit_engine.dispose()
            pytest.skip("pgvector not installed locally — skipping DB tests")
    await autocommit_engine.dispose()

    # Re-init DB on the test engine to ensure schema
    # Use raw DROP/CREATE SCHEMA to handle FK dependencies cleanly
    async with test_engine.begin() as conn:
        await conn.execute(sqlalchemy.text("DROP SCHEMA public CASCADE"))
        await conn.execute(sqlalchemy.text("CREATE SCHEMA public"))
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
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


# ---------------------------------------------------------------------------
# Shared Pop fixtures (used by test_pop_routes, test_pop_list, etc.)
# ---------------------------------------------------------------------------

POP_GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture(name="pop_user")
async def pop_user_fixture(session: AsyncSession):
    """Authenticated Pop user + valid session token."""
    from models import User, AuthSession, hash_token, generate_session_token

    user = User(email="pop_user@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()
    return user, token


@pytest_asyncio.fixture(name="other_user")
async def other_user_fixture(session: AsyncSession):
    """A second authenticated user (for ownership-boundary tests)."""
    from models import User, AuthSession, hash_token, generate_session_token

    user = User(email="other_pop@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()
    return user, token


@pytest_asyncio.fixture(name="guest_user")
async def guest_user_fixture(session: AsyncSession):
    """The shared guest user used by anonymous Pop chat."""
    from models import User

    user = User(email=POP_GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture(name="pop_project")
async def pop_project_fixture(session: AsyncSession, pop_user):
    """A 'Family Shopping List' project owned by pop_user."""
    from models import Project

    user, _ = pop_user
    project = Project(title="Family Shopping List", user_id=user.id, status="active")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@pytest_asyncio.fixture(name="pop_row")
async def pop_row_fixture(session: AsyncSession, pop_user, pop_project):
    """A sourcing row inside pop_project."""
    from models import Row

    user, _ = pop_user
    row = Row(
        title="Whole milk",
        status="sourcing",
        user_id=user.id,
        project_id=pop_project.id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@pytest_asyncio.fixture(name="pop_invite")
async def pop_invite_fixture(session: AsyncSession, pop_user, pop_project):
    """A valid (non-expired) invite for pop_project."""
    import uuid
    from datetime import datetime, timedelta
    from models import ProjectInvite

    user, _ = pop_user
    invite = ProjectInvite(
        id=str(uuid.uuid4()),
        project_id=pop_project.id,
        invited_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return invite
