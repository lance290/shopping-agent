"""Database-level regression tests for null/malformed JSONB fields.

Covers:
- Row with null JSONB columns (choice_factors, choice_answers, search_intent, etc.)
- Row with JSON null stored in JSONB columns
- Row serialization via API with null fields
- Bid filtering with null/empty choice_answers
- Row PATCH with null selected_providers
- Row creation with all nullable fields omitted
"""
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Bid, Project


# ---------------------------------------------------------------------------
# 1. Row creation with null JSONB fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_row_with_all_null_jsonb(session: AsyncSession, auth_user_and_token):
    """Row can be created and read with all JSONB columns as None."""
    user, _ = auth_user_and_token
    row = Row(
        title="All nulls",
        status="sourcing",
        user_id=user.id,
        choice_factors=None,
        choice_answers=None,
        search_intent=None,
        provider_query_map=None,
        chat_history=None,
        selected_providers=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.id is not None
    assert row.choice_factors is None
    assert row.choice_answers is None
    assert row.search_intent is None
    assert row.selected_providers is None


@pytest.mark.asyncio
async def test_create_row_with_empty_object_jsonb(session: AsyncSession, auth_user_and_token):
    """Row can store empty dicts/lists in JSONB columns."""
    user, _ = auth_user_and_token
    row = Row(
        title="Empty objects",
        status="sourcing",
        user_id=user.id,
        choice_factors=[],
        choice_answers={},
        search_intent={},
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.choice_factors == []
    assert row.choice_answers == {}
    assert row.search_intent == {}


@pytest.mark.asyncio
async def test_row_choice_answers_stores_and_retrieves_dict(session: AsyncSession, auth_user_and_token):
    """choice_answers round-trips as a dict through JSONB."""
    user, _ = auth_user_and_token
    answers = {"size": "M", "color": "blue", "min_price": 50}
    row = Row(
        title="Dict answers",
        status="sourcing",
        user_id=user.id,
        choice_answers=answers,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.choice_answers == answers
    assert row.choice_answers["size"] == "M"
    assert row.choice_answers["min_price"] == 50


@pytest.mark.asyncio
async def test_row_choice_factors_stores_array(session: AsyncSession, auth_user_and_token):
    """choice_factors round-trips as an array through JSONB."""
    user, _ = auth_user_and_token
    factors = [
        {"name": "size", "label": "Size", "type": "select", "options": ["S", "M", "L"]},
        {"name": "color", "label": "Color", "type": "text"},
    ]
    row = Row(
        title="Array factors",
        status="sourcing",
        user_id=user.id,
        choice_factors=factors,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert len(row.choice_factors) == 2
    assert row.choice_factors[0]["name"] == "size"


# ---------------------------------------------------------------------------
# 2. Row API serialization with null fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_get_rows_with_null_jsonb_fields(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """GET /rows returns rows with null JSONB fields without crashing."""
    user, token = auth_user_and_token

    # Create rows with various null states
    for i, (ca, cf) in enumerate([
        (None, None),
        ({}, []),
        ({"size": "M"}, [{"name": "size"}]),
    ]):
        row = Row(
            title=f"Null test {i}",
            status="sourcing",
            user_id=user.id,
            choice_answers=ca,
            choice_factors=cf,
        )
        session.add(row)

    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_api_get_single_row_with_null_fields(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """GET /rows/{id} returns a row with null JSONB fields."""
    user, token = auth_user_and_token
    row = Row(
        title="Single null row",
        status="sourcing",
        user_id=user.id,
        choice_answers=None,
        choice_factors=None,
        selected_providers=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    resp = await client.get(f"/rows/{row.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == row.id


# ---------------------------------------------------------------------------
# 3. Row PATCH with null/malformed selected_providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_row_selected_providers_null(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """PATCH /rows/{id} with selected_providers=null must not crash."""
    user, token = auth_user_and_token
    row = Row(title="Patch null test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    resp = await client.patch(
        f"/rows/{row.id}",
        json={"selected_providers": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should not crash (200 or 422 for validation)
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_patch_row_selected_providers_valid(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """PATCH /rows/{id} with valid selected_providers JSON."""
    user, token = auth_user_and_token
    row = Row(title="Patch valid test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    providers = json.dumps({"amazon": True, "ebay": False, "serpapi": True})
    resp = await client.patch(
        f"/rows/{row.id}",
        json={"selected_providers": providers},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Bid filtering with null choice_answers at DB level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bid_filtering_null_choice_answers_db(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """GET /rows returns bids even when choice_answers is null."""
    user, token = auth_user_and_token
    row = Row(
        title="Bid filter null test",
        status="sourcing",
        user_id=user.id,
        choice_answers=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        price=25.0,
        total_cost=25.0,
        item_title="Test Product",
        item_url="https://example.com/product",
        source="amazon",
    )
    session.add(bid)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    row_data = next(r for r in data if r["title"] == "Bid filter null test")
    assert len(row_data["bids"]) >= 1


@pytest.mark.asyncio
async def test_bid_filtering_empty_object_choice_answers_db(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """GET /rows returns bids when choice_answers is an empty dict."""
    user, token = auth_user_and_token
    row = Row(
        title="Bid filter empty test",
        status="sourcing",
        user_id=user.id,
        choice_answers={},
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        price=50.0,
        total_cost=50.0,
        item_title="Another Product",
        item_url="https://example.com/product2",
        source="ebay",
    )
    session.add(bid)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    row_data = next(r for r in data if r["title"] == "Bid filter empty test")
    assert len(row_data["bids"]) >= 1


# ---------------------------------------------------------------------------
# 5. Row with various desire_tier values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_row_desire_tier_values(session: AsyncSession, auth_user_and_token):
    """All valid desire_tier values can be stored and retrieved."""
    user, _ = auth_user_and_token
    tiers = ["commodity", "considered", "service", "bespoke", "high_value", "advisory"]
    for tier in tiers:
        row = Row(
            title=f"Tier {tier}",
            status="sourcing",
            user_id=user.id,
            desire_tier=tier,
        )
        session.add(row)
    await session.commit()

    result = await session.exec(
        select(Row).where(Row.user_id == user.id, Row.title.startswith("Tier "))
    )
    rows = result.all()
    assert len(rows) == len(tiers)
    stored_tiers = {r.desire_tier for r in rows}
    assert stored_tiers == set(tiers)


# ---------------------------------------------------------------------------
# 6. Row ownership isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_row_ownership_isolation_db(session: AsyncSession):
    """Rows are isolated by user_id — no cross-user leakage."""
    user_a = User(email="a@test.com", is_admin=False)
    user_b = User(email="b@test.com", is_admin=False)
    session.add_all([user_a, user_b])
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)

    row_a = Row(title="A's row", status="sourcing", user_id=user_a.id)
    row_b = Row(title="B's row", status="sourcing", user_id=user_b.id)
    session.add_all([row_a, row_b])
    await session.commit()

    result_a = await session.exec(select(Row).where(Row.user_id == user_a.id))
    result_b = await session.exec(select(Row).where(Row.user_id == user_b.id))

    rows_a = result_a.all()
    rows_b = result_b.all()

    assert len(rows_a) == 1
    assert rows_a[0].title == "A's row"
    assert len(rows_b) == 1
    assert rows_b[0].title == "B's row"


# ---------------------------------------------------------------------------
# 7. Project-Row relationship with null project_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_row_without_project(session: AsyncSession, auth_user_and_token):
    """Row can exist without a project."""
    user, _ = auth_user_and_token
    row = Row(title="No project", status="sourcing", user_id=user.id, project_id=None)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.project_id is None
    assert row.id is not None


@pytest.mark.asyncio
async def test_row_with_project(session: AsyncSession, auth_user_and_token):
    """Row correctly links to a project."""
    user, _ = auth_user_and_token
    project = Project(title="My Project", user_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    row = Row(title="In project", status="sourcing", user_id=user.id, project_id=project.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.project_id == project.id


# ---------------------------------------------------------------------------
# 8. search_intent JSONB round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_intent_dict_roundtrip(session: AsyncSession, auth_user_and_token):
    """search_intent stored as dict round-trips through JSONB."""
    user, _ = auth_user_and_token
    intent = {
        "product_name": "Gulfstream G650",
        "raw_input": "private jet",
        "min_price": 50000000,
    }
    row = Row(
        title="Intent test",
        status="sourcing",
        user_id=user.id,
        search_intent=intent,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.search_intent["product_name"] == "Gulfstream G650"
    assert row.search_intent["min_price"] == 50000000


@pytest.mark.asyncio
async def test_search_intent_null_roundtrip(session: AsyncSession, auth_user_and_token):
    """search_intent stored as None round-trips correctly."""
    user, _ = auth_user_and_token
    row = Row(
        title="Null intent",
        status="sourcing",
        user_id=user.id,
        search_intent=None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.search_intent is None
