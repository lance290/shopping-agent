"""Tests for the auth/verify endpoint processing referral codes during registration."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, AuthLoginCode, AuthSession, hash_token
from models.pop import Referral, WalletTransaction

@pytest_asyncio.fixture(name="referrer")
async def referrer_fixture(session: AsyncSession):
    user = User(email="referrer_auth@example.com", is_admin=False, ref_code="AUTHREF1")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@pytest.mark.asyncio
async def test_auth_verify_creates_referral_and_credits_wallet(
    client: AsyncClient,
    session: AsyncSession,
    referrer,
):
    """POST /auth/verify with ref_code attributes referral to the new user and credits referrer."""
    # 1. Setup login code for new user
    phone = "+16505550222"
    code = "123456"
    
    login_code = AuthLoginCode(
        email=None, 
        phone_number=phone, 
        code_hash=hash_token(code),
        is_active=True
    )
    session.add(login_code)
    await session.commit()
    
    initial_balance = referrer.wallet_balance_cents or 0
    
    # 2. Call auth/verify with ref_code
    # Mock Twilio/bypass handled by PYTEST_CURRENT_TEST environment variable
    resp = await client.post(
        "/auth/verify", 
        json={
            "phone": phone, 
            "code": code,
            "ref_code": "AUTHREF1"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    
    # 3. Verify User created with referred_by_id
    stmt = select(User).where(User.phone_number == phone)
    result = await session.execute(stmt)
    new_user = result.scalars().first()
    assert new_user is not None
    assert new_user.referred_by_id == referrer.id
    assert new_user.signup_source == "referral"
    
    # 4. Verify Referral record created
    ref_stmt = select(Referral).where(Referral.referred_user_id == new_user.id)
    ref_result = await session.execute(ref_stmt)
    referral = ref_result.scalar_one_or_none()
    assert referral is not None
    assert referral.referrer_user_id == referrer.id
    
    # 5. Verify WalletTransaction and Balance
    await session.refresh(referrer)
    assert referrer.wallet_balance_cents == initial_balance + 100
    
    txn_stmt = select(WalletTransaction).where(
        WalletTransaction.user_id == referrer.id,
        WalletTransaction.source == "referral_bonus"
    )
    txn_result = await session.execute(txn_stmt)
    txn = txn_result.scalar_one_or_none()
    assert txn is not None
    assert txn.amount_cents == 100
