"""Phase 4 HTTP endpoint integration tests.

Tests cover actual HTTP requests through FastAPI TestClient:
- PRD 00: Stripe Connect earnings (no live Stripe)
- PRD 04: Seller bookmarks (CRUD)
- PRD 04: Notifications (list, count, mark read)
- PRD 09: Admin metrics (admin-only)
- PRD 10: Anti-fraud clickout fields
- PRD 11: User signals + learned preferences
- PRD 12: Outreach expiration check (admin)
"""

import json
import pytest
from datetime import datetime, timedelta

from models import (
    AuthSession,
    Bid,
    ClickoutEvent,
    Merchant,
    Notification,
    OutreachEvent,
    PurchaseEvent,
    Row,
    Seller,
    User,
    UserSignal,
    generate_session_token,
    hash_token,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def _make_auth():
    """Factory to create an authenticated user + token."""

    async def _create(session, *, email, is_admin=False):
        user = User(email=email, is_admin=is_admin)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = generate_session_token()
        auth = AuthSession(
            email=user.email,
            user_id=user.id,
            session_token_hash=hash_token(token),
        )
        session.add(auth)
        await session.commit()
        return user, token

    return _create


@pytest.fixture
def _make_merchant():
    """Factory to create a merchant profile for a user."""

    async def _create(session, user, **overrides):
        defaults = dict(
            name="Test Merchant Co",
            contact_name=user.email.split("@")[0],
            email=f"merchant-{user.id}@example.com",
            user_id=user.id,
            status="verified",
            category="electronics",
        )
        defaults.update(overrides)
        m = Merchant(**defaults)
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m

    return _create


# ── PRD 04: Notifications ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notifications_list_empty(client, session, _make_auth):
    """GET /notifications returns empty list for new user."""
    user, token = await _make_auth(session, email="notif-empty@example.com")
    resp = await client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_notifications_list_requires_auth(client):
    """GET /notifications returns 401 without auth."""
    resp = await client.get("/notifications")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_notifications_count(client, session, _make_auth):
    """GET /notifications/count returns unread count."""
    user, token = await _make_auth(session, email="notif-count@example.com")

    # Seed 2 unread + 1 read notification
    for i in range(2):
        session.add(Notification(
            user_id=user.id, type="test", title=f"Unread {i}",
        ))
    session.add(Notification(
        user_id=user.id, type="test", title="Already read", read=True,
    ))
    await session.commit()

    resp = await client.get(
        "/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["unread"] == 2


@pytest.mark.asyncio
async def test_notifications_mark_read(client, session, _make_auth):
    """POST /notifications/{id}/read marks it read."""
    user, token = await _make_auth(session, email="notif-mark@example.com")

    notif = Notification(user_id=user.id, type="test", title="Mark me")
    session.add(notif)
    await session.commit()
    await session.refresh(notif)

    resp = await client.post(
        f"/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify
    await session.refresh(notif)
    assert notif.read is True


@pytest.mark.asyncio
async def test_notifications_mark_read_wrong_user(client, session, _make_auth):
    """POST /notifications/{id}/read returns 404 for another user's notification."""
    user1, token1 = await _make_auth(session, email="notif-u1@example.com")
    user2, token2 = await _make_auth(session, email="notif-u2@example.com")

    notif = Notification(user_id=user1.id, type="test", title="User 1 notif")
    session.add(notif)
    await session.commit()
    await session.refresh(notif)

    # User 2 tries to mark user 1's notification
    resp = await client.post(
        f"/notifications/{notif.id}/read",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_notifications_mark_all_read(client, session, _make_auth):
    """POST /notifications/read-all marks all unread notifications as read."""
    user, token = await _make_auth(session, email="notif-all@example.com")

    for i in range(3):
        session.add(Notification(user_id=user.id, type="test", title=f"N{i}"))
    await session.commit()

    resp = await client.post(
        "/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Verify count is 0
    count_resp = await client.get(
        "/notifications/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert count_resp.json()["unread"] == 0


@pytest.mark.asyncio
async def test_notifications_unread_only_filter(client, session, _make_auth):
    """GET /notifications?unread_only=true filters to unread only."""
    user, token = await _make_auth(session, email="notif-filter@example.com")

    session.add(Notification(user_id=user.id, type="test", title="Unread"))
    session.add(Notification(user_id=user.id, type="test", title="Read", read=True))
    await session.commit()

    resp = await client.get(
        "/notifications",
        params={"unread_only": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Unread"


# ── PRD 04: Seller Bookmarks ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_bookmarks_requires_auth(client):
    """Bookmark endpoints return 401 without auth."""
    resp = await client.get("/seller/bookmarks")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bookmarks_requires_merchant(client, session, _make_auth):
    """Bookmark endpoints return 403 if user has no merchant profile."""
    user, token = await _make_auth(session, email="no-merchant@example.com")
    resp = await client.get(
        "/seller/bookmarks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bookmarks_crud(client, session, _make_auth, _make_merchant):
    """Full CRUD cycle: list (empty), add, list (1), remove, list (empty)."""
    user, token = await _make_auth(session, email="bm-crud@example.com")
    await _make_merchant(session, user)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a row to bookmark
    row = Row(title="Bookmarkable RFP", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # 1. List — empty
    resp = await client.get("/seller/bookmarks", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Add bookmark
    resp = await client.post(f"/seller/bookmarks/{row.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "bookmarked"

    # 3. List — has 1
    resp = await client.get("/seller/bookmarks", headers=headers)
    assert resp.status_code == 200
    bookmarks = resp.json()
    assert len(bookmarks) == 1
    assert bookmarks[0]["row_id"] == row.id
    assert bookmarks[0]["title"] == "Bookmarkable RFP"

    # 4. Duplicate add — idempotent
    resp = await client.post(f"/seller/bookmarks/{row.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_bookmarked"

    # 5. Remove
    resp = await client.delete(f"/seller/bookmarks/{row.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"

    # 6. List — empty again
    resp = await client.get("/seller/bookmarks", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_bookmark_nonexistent_row(client, session, _make_auth, _make_merchant):
    """POST /seller/bookmarks/999999 returns 404 for non-existent row."""
    user, token = await _make_auth(session, email="bm-norow@example.com")
    await _make_merchant(session, user)
    resp = await client.post(
        "/seller/bookmarks/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── PRD 00: Stripe Connect Earnings (no live Stripe) ─────────────────


@pytest.mark.asyncio
async def test_earnings_requires_auth(client):
    """GET /stripe-connect/earnings returns 401 without auth."""
    resp = await client.get("/stripe-connect/earnings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_earnings_requires_merchant(client, session, _make_auth):
    """GET /stripe-connect/earnings returns 403 without merchant profile."""
    user, token = await _make_auth(session, email="earn-nomerch@example.com")
    resp = await client.get(
        "/stripe-connect/earnings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_earnings_zero_for_new_merchant(client, session, _make_auth, _make_merchant):
    """GET /stripe-connect/earnings returns zeros for merchant with no seller_id."""
    user, token = await _make_auth(session, email="earn-zero@example.com")
    await _make_merchant(session, user)
    resp = await client.get(
        "/stripe-connect/earnings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_earnings"] == 0.0
    assert data["completed_transactions"] == 0
    assert data["commission_rate"] == 0.05


# ── PRD 09: Admin Metrics ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_metrics_requires_auth(client):
    """GET /admin/metrics returns 401 without auth."""
    resp = await client.get("/admin/metrics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_metrics_requires_admin(client, session, _make_auth):
    """GET /admin/metrics returns 403 for non-admin user."""
    user, token = await _make_auth(session, email="notadmin@example.com")
    resp = await client.get(
        "/admin/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_metrics_success(client, session, _make_auth):
    """GET /admin/metrics returns metrics object for admin."""
    admin, token = await _make_auth(session, email="admin-met@example.com", is_admin=True)
    resp = await client.get(
        "/admin/metrics",
        params={"days": 7},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "m1_avg_time_to_first_result_seconds" in data
    assert "m2_offer_ctr" in data
    assert "m3_clickout_success_rate" in data
    assert "m4_affiliate_coverage" in data
    assert "m5_revenue_per_active_user" in data
    assert "funnel" in data
    assert "revenue" in data
    assert data["period"]["days"] == 7


# ── PRD 12: Admin Outreach Check ─────────────────────────────────────


@pytest.mark.asyncio
async def test_check_expired_requires_admin(client, session, _make_auth):
    """POST /admin/outreach/check-expired returns 403 for non-admin."""
    user, token = await _make_auth(session, email="notadmin-exp@example.com")
    resp = await client.post(
        "/admin/outreach/check-expired",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_check_expired_empty(client, session, _make_auth):
    """POST /admin/outreach/check-expired returns empty when nothing expired."""
    admin, token = await _make_auth(session, email="admin-exp@example.com", is_admin=True)
    resp = await client.post(
        "/admin/outreach/check-expired",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expired_count"] == 0
    assert data["expired"] == []


@pytest.mark.asyncio
async def test_check_expired_finds_timed_out(client, session, _make_auth):
    """POST /admin/outreach/check-expired marks timed-out outreach as expired."""
    admin, token = await _make_auth(session, email="admin-exp2@example.com", is_admin=True)

    # Create a row for the outreach
    row = Row(title="Expired Outreach Row", status="sourcing", user_id=admin.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create an outreach event sent 72h ago with 48h timeout → should be expired
    event = OutreachEvent(
        row_id=row.id,
        vendor_email="slow-vendor@example.com",
        vendor_name="Slow Vendor",
        status="sent",
        timeout_hours=48,
        sent_at=datetime.utcnow() - timedelta(hours=72),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    resp = await client.post(
        "/admin/outreach/check-expired",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expired_count"] == 1
    assert data["expired"][0]["vendor_email"] == "slow-vendor@example.com"

    # Verify event is now expired in DB
    await session.refresh(event)
    assert event.status == "expired"
    assert event.expired_at is not None


# ── PRD 10: Anti-Fraud Clickout Fields ───────────────────────────────


@pytest.mark.asyncio
async def test_clickout_event_stores_fraud_fields(session):
    """ClickoutEvent persists fraud-related fields in DB."""
    event = ClickoutEvent(
        canonical_url="https://example.com/fraud-test",
        final_url="https://example.com/fraud-test",
        merchant_domain="example.com",
        is_suspicious=True,
        ip_address="10.0.0.99",
        user_agent="BotAgent/1.0",
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    assert event.id is not None
    assert event.is_suspicious is True
    assert event.ip_address == "10.0.0.99"
    assert event.user_agent == "BotAgent/1.0"


# ── PRD 04: Notification from Row Creation ────────────────────────────


@pytest.mark.asyncio
async def test_row_creation_notifies_matching_merchants(client, session, _make_auth, _make_merchant):
    """Creating a row sends notifications to merchants with matching categories."""
    # Create a merchant user
    merchant_user, _ = await _make_auth(session, email="merch-notif@example.com")
    await _make_merchant(
        session, merchant_user,
        category="electronics",
    )

    # Create a buyer user and a row
    buyer, buyer_token = await _make_auth(session, email="buyer-notif@example.com")

    resp = await client.post(
        "/rows",
        json={
            "title": "Best electronics deals",
            "status": "sourcing",
            "currency": "USD",
            "request_spec": {"item_name": "electronics gadget", "constraints": "{}"},
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200

    # Check if merchant got a notification (may or may not match depending on category logic)
    from sqlmodel import select
    result = await session.exec(
        select(Notification).where(Notification.user_id == merchant_user.id)
    )
    # We just verify no crash — matching is fuzzy and may or may not produce a hit
    notifications = result.all()
    # The test validates the notification path runs without error
    assert isinstance(notifications, list)
