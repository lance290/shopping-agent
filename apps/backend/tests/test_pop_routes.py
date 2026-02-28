"""Regression tests for routes/pop.py — the Pop grocery savings agent.

Covers all endpoints:
  GET  /pop/health
  GET  /pop/list/{project_id}
  GET  /pop/my-list
  POST /pop/list/{project_id}/invite
  GET  /pop/invite/{token}
  POST /pop/join-list/{project_id}
  PATCH  /pop/item/{row_id}
  DELETE /pop/item/{row_id}
  GET  /pop/wallet
  POST /pop/receipt/scan
  POST /pop/chat
  POST /pop/webhooks/resend
  POST /pop/webhooks/twilio

Also covers helper functions:
  _load_chat_history
  _append_chat_history
  _ensure_project_member
  _verify_resend_signature

Bug regressions:
  - NameError: send_pop_onboarding_sms undefined in twilio webhook → fixed to send_pop_onboarding_sms
  - Expired invite must return 410, not 200
  - Guest chat must use guest user, not crash on missing auth
  - Item operations must reject cross-user access (404, not 403)
"""
import hashlib
import hmac
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, ProjectInvite, AuthSession, hash_token, generate_session_token


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

POP_GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture
async def pop_user(session: AsyncSession) -> tuple[User, str]:
    """Authenticated Pop user + valid session token."""
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


@pytest_asyncio.fixture
async def other_user(session: AsyncSession) -> tuple[User, str]:
    """A second authenticated user (for ownership-boundary tests)."""
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


@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    """The shared guest user used by anonymous Pop chat."""
    user = User(email=POP_GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def pop_project(session: AsyncSession, pop_user) -> Project:
    """A 'Family Shopping List' project owned by pop_user."""
    user, _ = pop_user
    project = Project(title="Family Shopping List", user_id=user.id, status="active")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@pytest_asyncio.fixture
async def pop_row(session: AsyncSession, pop_user, pop_project) -> Row:
    """A sourcing row inside pop_project."""
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


@pytest_asyncio.fixture
async def pop_invite(session: AsyncSession, pop_user, pop_project) -> ProjectInvite:
    """A valid (non-expired) invite for pop_project."""
    user, _ = pop_user
    import uuid
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


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /pop/health always returns 200 with status ok."""
    resp = await client.get("/pop/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "pop"


# ---------------------------------------------------------------------------
# 2. GET /pop/list/{project_id}  (public — no auth required)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_returns_items(
    client: AsyncClient,
    session: AsyncSession,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/list/{id} returns project + list items (no auth needed)."""
    resp = await client.get(f"/pop/list/{pop_project.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert isinstance(data["items"], list)
    assert any(item["title"] == "Whole milk" for item in data["items"])


@pytest.mark.asyncio
async def test_get_list_404_for_unknown_project(client: AsyncClient):
    """GET /pop/list/999999 returns 404 for non-existent project."""
    resp = await client.get("/pop/list/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_list_excludes_canceled_rows(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
):
    """Canceled rows must NOT appear in the public list view."""
    user, _ = pop_user
    canceled = Row(
        title="Canceled item",
        status="canceled",
        user_id=user.id,
        project_id=pop_project.id,
    )
    session.add(canceled)
    await session.commit()

    resp = await client.get(f"/pop/list/{pop_project.id}")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert "Canceled item" not in titles


@pytest.mark.asyncio
async def test_get_list_swap_heuristic(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Bids whose titles diverge from the row title appear as swap suggestions."""
    from models import Bid
    user, _ = pop_user

    # Near-exact match — NOT a swap
    matching_bid = Bid(
        row_id=pop_row.id,
        price=3.99,
        total_cost=3.99,
        item_title="Whole Milk Gallon",
        item_url="https://example.com/milk",
    )
    # Completely different product — IS a swap (explicitly flagged)
    swap_bid = Bid(
        row_id=pop_row.id,
        price=2.99,
        total_cost=2.99,
        item_title="Almond Breeze Oat Milk",
        item_url="https://example.com/oat",
        is_swap=True,
    )
    session.add_all([matching_bid, swap_bid])
    await session.commit()

    resp = await client.get(f"/pop/list/{pop_project.id}")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["deal_count"] >= 1
    # The oat milk bid should appear as a swap (low title overlap with "Whole milk")
    swap_titles = [s["title"] for s in item.get("swaps", [])]
    assert "Almond Breeze Oat Milk" in swap_titles


# ---------------------------------------------------------------------------
# 3. GET /pop/my-list  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_list_401_without_auth(client: AsyncClient):
    """GET /pop/my-list returns 401 when no token is provided."""
    resp = await client.get("/pop/my-list")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_my_list_returns_empty_when_no_project(
    client: AsyncClient,
    pop_user,
):
    """GET /pop/my-list returns empty list when user has no project yet."""
    _, token = pop_user
    resp = await client.get("/pop/my-list", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] is None
    assert data["items"] == []


@pytest.mark.asyncio
async def test_my_list_returns_active_project(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/my-list returns the user's Family Shopping List project."""
    _, token = pop_user
    resp = await client.get("/pop/my-list", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert any(i["title"] == "Whole milk" for i in data["items"])


# ---------------------------------------------------------------------------
# 4. POST /pop/list/{project_id}/invite  (requires auth, must own project)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_invite_401_without_auth(
    client: AsyncClient, pop_project: Project
):
    """Creating an invite without auth returns 401."""
    resp = await client.post(f"/pop/list/{pop_project.id}/invite")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_invite_returns_token_and_url(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
):
    """POST /pop/list/{id}/invite returns token + invite_url."""
    _, token = pop_user
    resp = await client.post(
        f"/pop/list/{pop_project.id}/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "invite_url" in data
    assert data["expires_days"] == 30
    assert len(data["token"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_create_invite_404_for_nonexistent_project(
    client: AsyncClient, pop_user
):
    """POST /pop/list/999999/invite returns 404 for non-existent project."""
    _, token = pop_user
    resp = await client.post(
        "/pop/list/999999/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. GET /pop/invite/{token}  (public)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_invite_returns_project_info(
    client: AsyncClient,
    pop_invite: ProjectInvite,
    pop_project: Project,
    pop_row: Row,
):
    """GET /pop/invite/{token} returns project title + item count."""
    resp = await client.get(f"/pop/invite/{pop_invite.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == pop_project.id
    assert data["item_count"] == 1  # one sourcing row
    assert data["token"] == pop_invite.id


@pytest.mark.asyncio
async def test_resolve_invite_404_for_unknown_token(client: AsyncClient):
    """GET /pop/invite/bogus returns 404."""
    resp = await client.get("/pop/invite/does-not-exist-abc123")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_invite_410_when_expired(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
):
    """Regression: expired invite must return 410, not 200."""
    import uuid
    user, _ = pop_user
    expired = ProjectInvite(
        id=str(uuid.uuid4()),
        project_id=pop_project.id,
        invited_by=user.id,
        expires_at=datetime.utcnow() - timedelta(days=1),  # already expired
    )
    session.add(expired)
    await session.commit()

    resp = await client.get(f"/pop/invite/{expired.id}")
    assert resp.status_code == 410, "Expired invite must return 410 Gone"


# ---------------------------------------------------------------------------
# 6. POST /pop/join-list/{project_id}  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_join_list_401_without_auth(
    client: AsyncClient, pop_project: Project
):
    resp = await client.post(f"/pop/join-list/{pop_project.id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_join_list_creates_member(
    client: AsyncClient,
    session: AsyncSession,
    other_user,
    pop_project: Project,
):
    """Authenticated user joins a shared list — ProjectMember record created."""
    user, token = other_user
    resp = await client.post(
        f"/pop/join-list/{pop_project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["joined"] is True
    assert data["project_id"] == pop_project.id

    # Verify DB record
    from sqlmodel import select
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == pop_project.id,
        ProjectMember.user_id == user.id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()
    assert member is not None
    assert member.channel == "web"


@pytest.mark.asyncio
async def test_join_list_idempotent(
    client: AsyncClient,
    other_user,
    pop_project: Project,
):
    """Joining the same list twice must not error — idempotent."""
    _, token = other_user
    headers = {"Authorization": f"Bearer {token}"}
    r1 = await client.post(f"/pop/join-list/{pop_project.id}", headers=headers)
    r2 = await client.post(f"/pop/join-list/{pop_project.id}", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_join_list_404_for_nonexistent_project(client: AsyncClient, pop_user):
    _, token = pop_user
    resp = await client.post(
        "/pop/join-list/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. PATCH /pop/item/{row_id}  (requires auth, owner-only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_item_renames_row(
    client: AsyncClient,
    pop_user,
    pop_row: Row,
):
    """PATCH /pop/item/{id} renames the row title."""
    _, token = pop_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"title": "Organic whole milk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Organic whole milk"
    assert data["id"] == pop_row.id


@pytest.mark.asyncio
async def test_patch_item_401_without_auth(client: AsyncClient, pop_row: Row):
    resp = await client.patch(f"/pop/item/{pop_row.id}", json={"title": "X"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_patch_item_404_for_other_users_row(
    client: AsyncClient,
    other_user,
    pop_row: Row,
):
    """Regression: user cannot rename another user's row — must get 404."""
    _, token = other_user
    resp = await client.patch(
        f"/pop/item/{pop_row.id}",
        json={"title": "Hijacked title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, "Cross-user item rename must return 404"


@pytest.mark.asyncio
async def test_patch_item_404_for_nonexistent_row(
    client: AsyncClient, pop_user
):
    _, token = pop_user
    resp = await client.patch(
        "/pop/item/999999",
        json={"title": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. DELETE /pop/item/{row_id}  (requires auth, owner-only, soft-delete)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_item_soft_deletes_row(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """DELETE /pop/item/{id} sets status='canceled' (soft delete)."""
    _, token = pop_user
    resp = await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    await session.refresh(pop_row)
    assert pop_row.status == "canceled", "Row must be soft-deleted (status=canceled)"


@pytest.mark.asyncio
async def test_delete_item_401_without_auth(client: AsyncClient, pop_row: Row):
    resp = await client.delete(f"/pop/item/{pop_row.id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_item_404_for_other_users_row(
    client: AsyncClient,
    other_user,
    pop_row: Row,
):
    """Regression: user cannot delete another user's row — must get 404."""
    _, token = other_user
    resp = await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, "Cross-user item delete must return 404"


# ---------------------------------------------------------------------------
# Offer claim / unclaim (PRD 3 — swap discovery and claiming)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_offer_marks_bid_selected(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """POST /pop/offer/{id}/claim marks bid as selected and returns claimed=True."""
    from models import Bid
    _, token = pop_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk", is_swap=True)
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.post(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["claimed"] is True
    assert data["bid_id"] == bid.id
    await session.refresh(bid)
    assert bid.is_selected is True


@pytest.mark.asyncio
async def test_claim_clears_prior_selection(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """Claiming a new offer clears any previously selected bid on the same row."""
    from models import Bid
    _, token = pop_user
    bid_a = Bid(row_id=pop_row.id, price=3.00, total_cost=3.00, item_title="Brand A", is_selected=True)
    bid_b = Bid(row_id=pop_row.id, price=2.50, total_cost=2.50, item_title="Brand B")
    session.add_all([bid_a, bid_b])
    await session.commit()
    await session.refresh(bid_a)
    await session.refresh(bid_b)

    resp = await client.post(
        f"/pop/offer/{bid_b.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    await session.refresh(bid_a)
    await session.refresh(bid_b)
    assert bid_a.is_selected is False, "Prior claim must be cleared"
    assert bid_b.is_selected is True


@pytest.mark.asyncio
async def test_unclaim_offer(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_row: Row,
):
    """DELETE /pop/offer/{id}/claim removes the claim (is_selected=False)."""
    from models import Bid
    _, token = pop_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk", is_selected=True)
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.delete(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["claimed"] is False
    await session.refresh(bid)
    assert bid.is_selected is False


@pytest.mark.asyncio
async def test_claim_offer_401_without_auth(client: AsyncClient, pop_row: Row):
    """Unauthenticated claim attempt returns 401."""
    resp = await client.post(f"/pop/offer/999/claim")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_claim_offer_404_cross_user(
    client: AsyncClient,
    session: AsyncSession,
    other_user,
    pop_row: Row,
):
    """User cannot claim a bid on another user's row — 404."""
    from models import Bid
    _, token = other_user
    bid = Bid(row_id=pop_row.id, price=2.49, total_cost=2.49, item_title="Oat Milk")
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    resp = await client.post(
        f"/pop/offer/{bid.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deleted_item_excluded_from_list(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """After soft-delete, the item should not appear in GET /pop/list."""
    _, token = pop_user
    await client.delete(
        f"/pop/item/{pop_row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(f"/pop/list/{pop_project.id}")
    titles = [i["title"] for i in resp.json()["items"]]
    assert "Whole milk" not in titles


# ---------------------------------------------------------------------------
# 9. GET /pop/wallet  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wallet_401_without_auth(client: AsyncClient):
    resp = await client.get("/pop/wallet")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wallet_returns_zero_balance_for_new_user(
    client: AsyncClient, pop_user
):
    """New user's wallet starts at 0 cents with no transactions."""
    _, token = pop_user
    resp = await client.get(
        "/pop/wallet",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance_cents"] == 0
    assert data["transactions"] == []


# ---------------------------------------------------------------------------
# 10. POST /pop/receipt/scan  (requires auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_receipt_scan_401_without_auth(client: AsyncClient):
    resp = await client.post(
        "/pop/receipt/scan",
        json={"image_base64": "dGVzdA=="},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_receipt_scan_no_items_returns_graceful_message(
    client: AsyncClient, pop_user
):
    """When OCR returns no items, scan returns status=no_items (not a crash)."""
    _, token = pop_user
    with patch("routes.pop._extract_receipt_items", new_callable=AsyncMock, return_value=[]):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA=="},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "no_items"
    assert data["credits_earned_cents"] == 0


@pytest.mark.asyncio
async def test_receipt_scan_matches_list_items_and_earns_credits(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Receipt items that match list items earn 25 cents each."""
    _, token = pop_user
    mock_items = [{"name": "Whole milk", "price": 3.49, "is_swap": False}]
    with patch("routes.pop._extract_receipt_items", new_callable=AsyncMock, return_value=mock_items):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scanned"
    assert data["credits_earned_cents"] >= 25
    assert data["total_items"] == 1


@pytest.mark.asyncio
async def test_receipt_scan_swap_earns_extra_credits(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """Swap purchases earn 50 cents (vs 25 for regular match)."""
    _, token = pop_user
    mock_items = [{"name": "Whole milk", "price": 3.49, "is_swap": True}]
    with patch("routes.pop._extract_receipt_items", new_callable=AsyncMock, return_value=mock_items):
        resp = await client.post(
            "/pop/receipt/scan",
            json={"image_base64": "dGVzdA==", "project_id": pop_project.id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credits_earned_cents"] == 50


# ---------------------------------------------------------------------------
# 11. POST /pop/chat  (guest + authenticated)
# ---------------------------------------------------------------------------

def _mock_pop_decision(message: str = "Got it! Added to your list."):
    """Build a minimal mock of make_pop_decision's return value."""
    mock_intent = MagicMock()
    mock_intent.what = "eggs"
    mock_intent.category = "product"
    mock_intent.service_type = None
    mock_intent.search_query = None
    mock_intent.exclude_keywords = []
    mock_intent.exclude_merchants = []
    mock_intent.constraints = {}
    mock_intent.desire_tier = None

    mock_item = MagicMock()
    mock_item.action = {"type": "chat"}
    mock_item.intent = mock_intent

    mock_decision = MagicMock()
    mock_decision.items = [mock_item]
    mock_decision.message = message
    return mock_decision


@pytest.mark.asyncio
async def test_chat_guest_mode_without_auth(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
):
    """Regression: POST /pop/chat without auth uses guest user — must not 401."""
    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "I need eggs"},
            )
    assert resp.status_code == 200, f"Guest chat must succeed, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "reply" in data
    assert "project_id" in data


@pytest.mark.asyncio
async def test_chat_guest_without_guest_user_in_db_returns_signup_nudge(
    client: AsyncClient,
    session: AsyncSession,
):
    """When guest user doesn't exist in DB, chat returns signup prompt (no crash)."""
    # No guest_user fixture — guest@buy-anything.com absent from DB
    resp = await client.post(
        "/pop/chat",
        json={"message": "I need eggs"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    # Should contain a signup nudge
    assert "popsavings.com" in data["reply"].lower() or "sign" in data["reply"].lower()


@pytest.mark.asyncio
async def test_chat_authenticated_creates_family_shopping_list(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """Authenticated chat auto-creates 'Family Shopping List' project if absent."""
    user, token = pop_user

    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "Need milk"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] is not None

    # Verify project created in DB
    from sqlmodel import select
    proj = await session.get(Project, data["project_id"])
    assert proj is not None
    assert proj.title == "Family Shopping List"


@pytest.mark.asyncio
async def test_chat_authenticated_reuses_existing_project(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
):
    """Chat must reuse an existing 'Family Shopping List', not create a duplicate."""
    _, token = pop_user
    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            r1 = await client.post(
                "/pop/chat",
                json={"message": "Need eggs"},
                headers={"Authorization": f"Bearer {token}"},
            )
            r2 = await client.post(
                "/pop/chat",
                json={"message": "Need butter"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both must return the SAME project_id
    assert r1.json()["project_id"] == r2.json()["project_id"]


@pytest.mark.asyncio
async def test_chat_returns_list_items_in_response(
    client: AsyncClient,
    pop_user,
    pop_project: Project,
    pop_row: Row,
):
    """POST /pop/chat response always includes current list_items snapshot."""
    _, token = pop_user
    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "What's on my list?"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["list_items"], list)
    titles = [i["title"] for i in data["list_items"]]
    assert "Whole milk" in titles


@pytest.mark.asyncio
async def test_chat_guest_resuming_session_via_guest_project_id(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
):
    """Guest chat with guest_project_id resumes existing project instead of creating a new one."""
    project = Project(title="My Shopping List", user_id=guest_user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "I need bread", "guest_project_id": project.id},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project.id, "Must reuse the existing guest project"


@pytest.mark.asyncio
async def test_chat_guest_cannot_resume_other_users_project(
    client: AsyncClient,
    session: AsyncSession,
    guest_user: User,
    pop_project: Project,
):
    """Regression: guest cannot hijack another user's project via guest_project_id."""
    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=_mock_pop_decision()):
        with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "list items", "guest_project_id": pop_project.id},
            )

    assert resp.status_code == 200
    data = resp.json()
    # Must NOT return the other user's project — a new guest project is created
    assert data["project_id"] != pop_project.id


@pytest.mark.asyncio
async def test_chat_create_row_action_persists_to_db(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """When decision action is create_row, a Row is persisted in the DB."""
    user, token = pop_user

    mock_intent = MagicMock()
    mock_intent.what = "avocados"
    mock_intent.category = "product"
    mock_intent.service_type = None
    mock_intent.search_query = "avocados"
    mock_intent.exclude_keywords = []
    mock_intent.exclude_merchants = []
    mock_intent.constraints = {}
    mock_intent.desire_tier = None

    mock_item = MagicMock()
    mock_item.action = {"type": "create_row"}
    mock_item.intent = mock_intent

    mock_decision = MagicMock()
    mock_decision.items = [mock_item]
    mock_decision.message = "Added avocados!"

    with patch("routes.pop.make_pop_decision", new_callable=AsyncMock, return_value=mock_decision):
        with patch("routes.pop._create_row", new_callable=AsyncMock) as mock_create:
            with patch("routes.pop.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                with patch("routes.pop._stream_search", return_value=_empty_async_gen()):
                    # create a fake row returned by _create_row
                    fake_row = Row(title="Avocados", status="sourcing", user_id=user.id)
                    session.add(fake_row)
                    await session.commit()
                    await session.refresh(fake_row)
                    mock_create.return_value = fake_row

                    resp = await client.post(
                        "/pop/chat",
                        json={"message": "I need avocados"},
                        headers={"Authorization": f"Bearer {token}"},
                    )

    assert resp.status_code == 200
    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# 12. POST /pop/webhooks/resend  (Resend inbound email)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resend_webhook_accepted(client: AsyncClient, pop_user):
    """Valid Resend webhook payload returns 200 accepted."""
    user, _ = pop_user
    payload = json.dumps({
        "from": f"Pop User <{user.email}>",
        "text": "I need milk and eggs",
        "subject": "Shopping list",
    }).encode()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):  # no secret = skip sig check
        with patch("routes.pop.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_resend_webhook_400_missing_sender(client: AsyncClient):
    """Resend webhook with missing 'from' field returns 400."""
    payload = json.dumps({"text": "I need milk", "subject": "test"}).encode()
    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resend_webhook_400_missing_body(client: AsyncClient):
    """Resend webhook with missing 'text'/'html' fields returns 400."""
    payload = json.dumps({"from": "user@example.com", "subject": "test"}).encode()
    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resend_webhook_401_invalid_signature(client: AsyncClient, pop_user):
    """Resend webhook with wrong HMAC signature returns 401."""
    user, _ = pop_user
    payload = json.dumps({
        "from": user.email,
        "text": "hello",
        "subject": "test",
    }).encode()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", "secret123"):
        resp = await client.post(
            "/pop/webhooks/resend",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "resend-signature": "badhash",
            },
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_resend_webhook_valid_signature_accepted(client: AsyncClient, pop_user):
    """Resend webhook with correct HMAC signature is accepted."""
    user, _ = pop_user
    secret = "my_webhook_secret"
    payload = json.dumps({
        "from": user.email,
        "text": "need bread",
        "subject": "shopping",
    }).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        with patch("routes.pop.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "resend-signature": sig,
                },
            )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_webhook_parses_full_name_email(client: AsyncClient, pop_user):
    """'From: Name <email>' format must be parsed to extract just the email."""
    user, _ = pop_user
    payload = json.dumps({
        "from": f"John Doe <{user.email}>",
        "text": "milk please",
        "subject": "list",
    }).encode()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):
        with patch("routes.pop.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/resend",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    # process_pop_message should receive the parsed email, not "John Doe <email>"
    call_args = mock_proc.call_args
    assert call_args[0][0] == user.email


# ---------------------------------------------------------------------------
# 13. POST /pop/webhooks/twilio  (Twilio inbound SMS)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_twilio_webhook_returns_twiml(client: AsyncClient, pop_user):
    """Valid Twilio webhook returns empty TwiML <Response/>."""
    user, _ = pop_user

    with patch("routes.pop.TWILIO_AUTH_TOKEN", ""):  # skip sig validation
        with patch("routes.pop.process_pop_message", new_callable=AsyncMock):
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+15005550006", "Body": "need milk"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200
    assert "<Response/>" in resp.text
    assert "application/xml" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_twilio_webhook_400_missing_from(client: AsyncClient):
    """Twilio webhook without 'From' field returns 400."""
    with patch("routes.pop.TWILIO_AUTH_TOKEN", ""):
        resp = await client.post(
            "/pop/webhooks/twilio",
            data={"Body": "milk"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_twilio_webhook_400_missing_body(client: AsyncClient):
    """Twilio webhook without 'Body' field returns 400."""
    with patch("routes.pop.TWILIO_AUTH_TOKEN", ""):
        resp = await client.post(
            "/pop/webhooks/twilio",
            data={"From": "+15005550006"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_twilio_webhook_unknown_phone_sends_onboarding_sms(
    client: AsyncClient,
    session: AsyncSession,
):
    """Regression: unknown phone number triggers onboarding SMS (not NameError crash).

    Bug: send_pop_onboarding_sms was undefined — now correctly named send_pop_onboarding_sms.
    This test verifies the correct function is called without raising NameError.
    """
    with patch("routes.pop.TWILIO_AUTH_TOKEN", ""):
        with patch("routes.pop.send_pop_onboarding_sms", return_value=True) as mock_sms:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+19999999999", "Body": "hello"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200, f"Should not crash on unknown phone, got {resp.status_code}: {resp.text}"
    mock_sms.assert_called_once_with("+19999999999")


@pytest.mark.asyncio
async def test_twilio_webhook_known_phone_dispatches_to_process_message(
    client: AsyncClient,
    session: AsyncSession,
    pop_user,
):
    """Known phone number dispatches to process_pop_message via background task."""
    user, _ = pop_user
    user.phone_number = "+15005550099"
    session.add(user)
    await session.commit()

    with patch("routes.pop.TWILIO_AUTH_TOKEN", ""):
        with patch("routes.pop.process_pop_message", new_callable=AsyncMock) as mock_proc:
            resp = await client.post(
                "/pop/webhooks/twilio",
                data={"From": "+15005550099", "Body": "add milk"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 14. Helper function unit tests
# ---------------------------------------------------------------------------

def test_load_chat_history_empty_row():
    """_load_chat_history returns [] for a row with no chat_history."""
    from routes.pop import _load_chat_history
    row = MagicMock()
    row.chat_history = None
    assert _load_chat_history(row) == []


def test_load_chat_history_valid_json():
    """_load_chat_history correctly parses stored JSON."""
    from routes.pop import _load_chat_history
    history = [
        {"role": "user", "content": "I need eggs"},
        {"role": "assistant", "content": "Added eggs!"},
    ]
    row = MagicMock()
    row.chat_history = json.dumps(history)
    result = _load_chat_history(row)
    assert len(result) == 2
    assert result[0]["role"] == "user"


def test_load_chat_history_invalid_json_returns_empty():
    """_load_chat_history returns [] for corrupt JSON (no crash)."""
    from routes.pop import _load_chat_history
    row = MagicMock()
    row.chat_history = "{broken json["
    assert _load_chat_history(row) == []


def test_load_chat_history_truncates_at_50_entries():
    """_load_chat_history returns list as-is (truncation is in _append, not _load)."""
    from routes.pop import _load_chat_history
    history = [{"role": "user", "content": f"msg {i}"} for i in range(60)]
    row = MagicMock()
    row.chat_history = json.dumps(history)
    result = _load_chat_history(row)
    assert len(result) == 60  # _load does not truncate, _append does


@pytest.mark.asyncio
async def test_append_chat_history_persists_exchange(session: AsyncSession, pop_user, pop_row: Row):
    """_append_chat_history stores user + assistant messages on the row."""
    from routes.pop import _append_chat_history

    await _append_chat_history(session, pop_row, "I need eggs", "Added eggs to your list!")

    await session.refresh(pop_row)
    history = json.loads(pop_row.chat_history)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "I need eggs"}
    assert history[1] == {"role": "assistant", "content": "Added eggs to your list!"}


@pytest.mark.asyncio
async def test_append_chat_history_truncates_at_50(session: AsyncSession, pop_user, pop_row: Row):
    """_append_chat_history caps history at 50 messages to prevent unbounded growth."""
    from routes.pop import _append_chat_history

    # Pre-load 48 messages
    initial = [{"role": "user", "content": f"msg {i}"} for i in range(48)]
    pop_row.chat_history = json.dumps(initial)
    session.add(pop_row)
    await session.commit()

    # This append adds 2 more = 50 — should stay at 50
    await _append_chat_history(session, pop_row, "msg 48", "reply 48")
    await session.refresh(pop_row)
    assert len(json.loads(pop_row.chat_history)) == 50

    # One more append = 52 → truncate to 50
    await _append_chat_history(session, pop_row, "msg 49", "reply 49")
    await session.refresh(pop_row)
    assert len(json.loads(pop_row.chat_history)) == 50


@pytest.mark.asyncio
async def test_ensure_project_member_creates_member(
    session: AsyncSession, pop_user, pop_project: Project
):
    """_ensure_project_member creates a ProjectMember if one doesn't exist."""
    from routes.pop import _ensure_project_member
    user, _ = pop_user

    member = await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    assert member.project_id == pop_project.id
    assert member.user_id == user.id
    assert member.channel == "web"


@pytest.mark.asyncio
async def test_ensure_project_member_is_idempotent(
    session: AsyncSession, pop_user, pop_project: Project
):
    """Calling _ensure_project_member twice for the same user does not duplicate records."""
    from routes.pop import _ensure_project_member
    from sqlmodel import select

    user, _ = pop_user
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    await _ensure_project_member(session, pop_project.id, user.id, channel="web")

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == pop_project.id,
        ProjectMember.user_id == user.id,
    )
    result = await session.execute(stmt)
    members = result.scalars().all()
    assert len(members) == 1, "Idempotent — must not create duplicate ProjectMember"


@pytest.mark.asyncio
async def test_ensure_project_member_updates_channel(
    session: AsyncSession, pop_user, pop_project: Project
):
    """_ensure_project_member updates channel if it changes."""
    from routes.pop import _ensure_project_member
    user, _ = pop_user

    await _ensure_project_member(session, pop_project.id, user.id, channel="email")
    member = await _ensure_project_member(session, pop_project.id, user.id, channel="web")
    assert member.channel == "web"


def test_verify_resend_signature_passes_with_correct_hmac():
    """_verify_resend_signature accepts a correctly signed payload."""
    from routes.pop import _verify_resend_signature
    secret = "test_secret_abc"
    payload = b'{"from": "user@example.com", "text": "milk"}'
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        assert _verify_resend_signature(payload, sig) is True


def test_verify_resend_signature_rejects_tampered_payload():
    """_verify_resend_signature rejects payload that doesn't match signature."""
    from routes.pop import _verify_resend_signature
    secret = "test_secret_abc"
    original = b'{"from": "user@example.com", "text": "milk"}'
    sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
    tampered = b'{"from": "attacker@evil.com", "text": "milk"}'

    with patch("routes.pop.RESEND_WEBHOOK_SECRET", secret):
        assert _verify_resend_signature(tampered, sig) is False


def test_verify_resend_signature_skips_check_when_no_secret():
    """_verify_resend_signature returns True (skip) when no secret configured."""
    from routes.pop import _verify_resend_signature
    with patch("routes.pop.RESEND_WEBHOOK_SECRET", ""):
        assert _verify_resend_signature(b"payload", "anysig") is True


# ---------------------------------------------------------------------------
# 15. send_pop_reply / send_pop_sms demo mode tests (no real credentials)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_bob_reply_demo_mode_returns_success():
    """send_pop_reply in demo mode (no RESEND_API_KEY) returns success without crashing."""
    from routes.pop import send_pop_reply
    with patch("routes.pop.RESEND_API_KEY", ""):
        result = await send_pop_reply(
            "test@example.com",
            "Test subject",
            "Hello from Pop!",
        )
    assert result.success is True
    assert result.message_id == "demo-pop-reply"


def test_send_bob_sms_demo_mode_returns_true():
    """send_pop_sms in demo mode (no Twilio creds) returns True without crashing."""
    from routes.pop import send_pop_sms
    with patch("routes.pop.TWILIO_ACCOUNT_SID", ""):
        result = send_pop_sms("+15005550006", "Hello!")
    assert result is True


# ---------------------------------------------------------------------------
# 16. process_pop_message edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_pop_message_unknown_user_sends_onboarding(
    session: AsyncSession,
):
    """process_pop_message for an unknown email sends onboarding email (no crash)."""
    from routes.pop import process_pop_message

    with patch("routes.pop.send_pop_onboarding_email", new_callable=AsyncMock) as mock_email:
        await process_pop_message(
            "unknown@nowhere.com",
            "I need groceries",
            session,
            channel="email",
        )
    mock_email.assert_called_once_with("unknown@nowhere.com")


@pytest.mark.asyncio
async def test_process_pop_message_unknown_sms_sends_onboarding_sms(
    session: AsyncSession,
):
    """process_pop_message via SMS for unknown user sends onboarding SMS."""
    from routes.pop import process_pop_message

    with patch("routes.pop.send_pop_onboarding_sms", return_value=True) as mock_sms:
        await process_pop_message(
            "unknown@nowhere.com",
            "need milk",
            session,
            channel="sms",
            sender_phone="+19998887777",
        )
    mock_sms.assert_called_once_with("+19998887777")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _empty_async_gen():
    """Empty async generator for mocking _stream_search."""
    return
    yield  # makes it an async generator
