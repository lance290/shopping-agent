"""Tests for Pop referral system routes (PRD-06: Dual CopyLink Growth System).

Covers:
  - GET /pop/referral — returns ref_code and referral link, auto-generates if missing
  - POST /pop/referral/signup — records referral, credits wallet, idempotent
  - POST /pop/referral/signup — rejects self-referral, invalid codes
  - Wallet balance incremented on referral attribution
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, AuthSession, hash_token, generate_session_token
from models.pop import Referral, WalletTransaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(name="referrer")
async def referrer_fixture(session: AsyncSession):
    """Authenticated user who will be the referrer."""
    user = User(email="referrer@example.com", is_admin=False, ref_code="REFTEST1")
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


@pytest_asyncio.fixture(name="new_user")
async def new_user_fixture(session: AsyncSession):
    """Authenticated user who signed up via a referral link."""
    user = User(email="newuser@example.com", is_admin=False)
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


# ---------------------------------------------------------------------------
# GET /pop/referral
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_referral_returns_existing_code(
    client: AsyncClient, referrer,
):
    """GET /pop/referral returns the user's existing ref_code and link."""
    user, token = referrer
    resp = await client.get(
        "/pop/referral",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ref_code"] == "REFTEST1"
    assert "REFTEST1" in data["referral_link"]
    assert data["total_referrals"] == 0


@pytest.mark.asyncio
async def test_get_referral_auto_generates_code(
    client: AsyncClient, new_user,
):
    """GET /pop/referral auto-generates a ref_code when user has none."""
    user, token = new_user
    assert user.ref_code is None  # no code yet

    resp = await client.get(
        "/pop/referral",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ref_code"] is not None
    assert len(data["ref_code"]) > 0
    assert "ref=" in data["referral_link"]


@pytest.mark.asyncio
async def test_get_referral_401_without_auth(client: AsyncClient):
    """GET /pop/referral returns 401 for unauthenticated request."""
    resp = await client.get("/pop/referral")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /pop/referral/signup — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_referral_signup_credits_referrer_wallet(
    client: AsyncClient,
    session: AsyncSession,
    referrer,
    new_user,
):
    """POST /pop/referral/signup credits the referrer's wallet with $1.00."""
    ref_user, _ = referrer
    _, new_token = new_user
    initial_balance = ref_user.wallet_balance_cents or 0

    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "attributed"
    assert data["referrer_id"] == ref_user.id

    # Verify wallet balance increased by 100 cents ($1.00)
    await session.refresh(ref_user)
    assert ref_user.wallet_balance_cents == initial_balance + 100


@pytest.mark.asyncio
async def test_referral_signup_creates_referral_record(
    client: AsyncClient,
    session: AsyncSession,
    referrer,
    new_user,
):
    """POST /pop/referral/signup creates a Referral record linking both users."""
    ref_user, _ = referrer
    nu, new_token = new_user

    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp.status_code == 200

    from sqlmodel import select
    stmt = select(Referral).where(Referral.referred_user_id == nu.id)
    result = await session.execute(stmt)
    referral = result.scalar_one_or_none()
    assert referral is not None
    assert referral.referrer_user_id == ref_user.id
    assert referral.status == "activated"


@pytest.mark.asyncio
async def test_referral_signup_creates_wallet_transaction(
    client: AsyncClient,
    session: AsyncSession,
    referrer,
    new_user,
):
    """POST /pop/referral/signup creates a WalletTransaction for the referrer."""
    ref_user, _ = referrer
    _, new_token = new_user

    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp.status_code == 200

    from sqlmodel import select
    stmt = select(WalletTransaction).where(
        WalletTransaction.user_id == ref_user.id,
        WalletTransaction.source == "referral_bonus",
    )
    result = await session.execute(stmt)
    txn = result.scalar_one_or_none()
    assert txn is not None
    assert txn.amount_cents == 100


@pytest.mark.asyncio
async def test_referral_signup_uses_oldest_matching_referrer_when_ref_code_is_duplicated(
    client: AsyncClient,
    session: AsyncSession,
    new_user,
):
    primary_referrer = User(email="primary_referrer@example.com", is_admin=False, ref_code="REFTEST1")
    duplicate_referrer = User(email="duplicate_referrer@example.com", is_admin=False, ref_code="REFTEST1")
    session.add(primary_referrer)
    session.add(duplicate_referrer)
    await session.commit()
    await session.refresh(primary_referrer)

    nu, new_token = new_user

    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["referrer_id"] == primary_referrer.id

    from sqlmodel import select
    result = await session.execute(select(Referral).where(Referral.referred_user_id == nu.id))
    referral = result.scalar_one_or_none()
    assert referral is not None
    assert referral.referrer_user_id == primary_referrer.id


# ---------------------------------------------------------------------------
# POST /pop/referral/signup — edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_referral_signup_idempotent(
    client: AsyncClient,
    session: AsyncSession,
    referrer,
    new_user,
):
    """Duplicate referral signup returns 'already_attributed' and doesn't double-credit."""
    ref_user, _ = referrer
    _, new_token = new_user

    # First signup
    resp1 = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "attributed"

    await session.refresh(ref_user)
    balance_after_first = ref_user.wallet_balance_cents

    # Second signup (duplicate)
    resp2 = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_attributed"

    # Balance unchanged
    await session.refresh(ref_user)
    assert ref_user.wallet_balance_cents == balance_after_first


@pytest.mark.asyncio
async def test_referral_signup_rejects_self_referral(
    client: AsyncClient, referrer,
):
    """Cannot refer yourself."""
    _, token = referrer
    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_referral_signup_rejects_invalid_code(
    client: AsyncClient, new_user,
):
    """Invalid ref code returns 404."""
    _, token = new_user
    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "INVALIDCODE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_referral_signup_rejects_empty_code(
    client: AsyncClient, new_user,
):
    """Empty ref code returns 400."""
    _, token = new_user
    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_referral_signup_401_without_auth(client: AsyncClient):
    """POST /pop/referral/signup returns 401 without auth."""
    resp = await client.post(
        "/pop/referral/signup",
        json={"ref_code": "REFTEST1"},
    )
    assert resp.status_code == 401
