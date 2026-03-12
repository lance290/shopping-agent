"""Tests for vendor trust model, contact quality scoring, and endorsement API."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Unit tests: Vendor.contact_quality_score
# ---------------------------------------------------------------------------

class TestContactQualityScore:
    def test_full_contact_info(self):
        from models.bids import Vendor
        v = Vendor(
            name="Test Vendor",
            phone="+1-555-1234",
            email="test@example.com",
            website="https://example.com",
            contact_name="John Doe",
            contact_form_url="https://example.com/contact",
            description="A test vendor",
        )
        assert v.contact_quality_score == 1.0

    def test_no_contact_info(self):
        from models.bids import Vendor
        v = Vendor(name="Empty Vendor")
        assert v.contact_quality_score == 0.0

    def test_partial_contact_info(self):
        from models.bids import Vendor
        v = Vendor(
            name="Partial Vendor",
            phone="+1-555-1234",
            email="test@example.com",
        )
        # phone=0.25, email=0.20
        assert v.contact_quality_score == 0.45

    def test_website_only(self):
        from models.bids import Vendor
        v = Vendor(name="Web Vendor", website="https://example.com")
        assert v.contact_quality_score == 0.20

    def test_booking_url_counts(self):
        from models.bids import Vendor
        v = Vendor(
            name="Booking Vendor",
            booking_url="https://example.com/book",
            description="Bookable",
        )
        # booking_url=0.10, description=0.10
        assert v.contact_quality_score == 0.20

    def test_contact_form_counts_same_as_booking(self):
        from models.bids import Vendor
        v = Vendor(
            name="Form Vendor",
            contact_form_url="https://example.com/contact",
        )
        # contact_form_url=0.10
        assert v.contact_quality_score == 0.10

    def test_high_quality_threshold(self):
        """Vendor with phone+email+website passes the 0.7 'Verified Contact' threshold."""
        from models.bids import Vendor
        v = Vendor(
            name="Quality Vendor",
            phone="+1-555-1234",
            email="q@example.com",
            website="https://quality.com",
            contact_name="Jane",
        )
        # phone=0.25, email=0.20, website=0.20, contact_name=0.15 = 0.80
        assert v.contact_quality_score >= 0.7


# ---------------------------------------------------------------------------
# Unit tests: Vendor trust model fields
# ---------------------------------------------------------------------------

class TestVendorTrustFields:
    def test_new_fields_have_defaults(self):
        from models.bids import Vendor
        v = Vendor(name="Default Vendor")
        assert v.vendor_type is None
        assert v.contact_title is None
        assert v.contact_form_url is None
        assert v.booking_url is None
        assert v.secondary_categories is None
        assert v.service_regions is None
        assert v.source_provenance is None
        assert v.trust_score is None
        assert v.last_verified_at is None
        assert v.last_contact_validated_at is None

    def test_vendor_type_can_be_set(self):
        from models.bids import Vendor
        v = Vendor(name="Broker Vendor", vendor_type="broker")
        assert v.vendor_type == "broker"


# ---------------------------------------------------------------------------
# Unit tests: VendorEndorsement model
# ---------------------------------------------------------------------------

class TestVendorEndorsementModel:
    def test_endorsement_fields(self):
        from models.bids import VendorEndorsement
        e = VendorEndorsement(
            vendor_id=1,
            user_id=2,
            trust_rating=5,
            notes="Great vendor",
            is_personal_contact=True,
        )
        assert e.vendor_id == 1
        assert e.user_id == 2
        assert e.trust_rating == 5
        assert e.is_personal_contact is True


# ---------------------------------------------------------------------------
# Integration tests: Endorsement API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endorsement_create(client: AsyncClient, session, auth_user_and_token):
    """POST /api/vendors/{id}/endorsements creates an endorsement."""
    from models.bids import Vendor

    user, token = auth_user_and_token

    vendor = Vendor(name="Endorse Target", email="e@test.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    resp = await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={
            "vendor_id": vendor.id,
            "trust_rating": 4,
            "notes": "Reliable vendor",
            "is_personal_contact": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendor_id"] == vendor.id
    assert data["trust_rating"] == 4
    assert data["is_personal_contact"] is True


@pytest.mark.asyncio
async def test_endorsement_upsert(client: AsyncClient, session, auth_user_and_token):
    """Second POST to same vendor updates the existing endorsement."""
    from models.bids import Vendor

    user, token = auth_user_and_token

    vendor = Vendor(name="Upsert Target", email="u@test.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    # First create
    resp1 = await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={"vendor_id": vendor.id, "trust_rating": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 200
    eid = resp1.json()["id"]

    # Upsert (update)
    resp2 = await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={"vendor_id": vendor.id, "trust_rating": 5, "notes": "Updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["id"] == eid  # same endorsement updated
    assert data["trust_rating"] == 5
    assert data["notes"] == "Updated"


@pytest.mark.asyncio
async def test_endorsement_list_for_vendor(client: AsyncClient, session, auth_user_and_token):
    """GET /api/vendors/{id}/endorsements lists endorsements."""
    from models.bids import Vendor

    user, token = auth_user_and_token

    vendor = Vendor(name="List Target")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    # Create endorsement
    await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={"vendor_id": vendor.id, "trust_rating": 4},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/vendors/{vendor.id}/endorsements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["endorsements"]) == 1
    assert data["endorsements"][0]["trust_rating"] == 4


@pytest.mark.asyncio
async def test_endorsement_delete(client: AsyncClient, session, auth_user_and_token):
    """DELETE /api/vendors/{id}/endorsements deletes user's endorsement."""
    from models.bids import Vendor

    user, token = auth_user_and_token

    vendor = Vendor(name="Delete Target")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={"vendor_id": vendor.id, "trust_rating": 3},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.delete(
        f"/api/vendors/{vendor.id}/endorsements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Verify it's gone
    resp2 = await client.get(
        f"/api/vendors/{vendor.id}/endorsements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(resp2.json()["endorsements"]) == 0


@pytest.mark.asyncio
async def test_endorsement_requires_auth(client: AsyncClient, session):
    """Endorsement endpoints require authentication."""
    from models.bids import Vendor

    vendor = Vendor(name="Auth Target")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    resp = await client.post(
        f"/api/vendors/{vendor.id}/endorsements",
        json={"vendor_id": vendor.id, "trust_rating": 3},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endorsement_vendor_not_found(client: AsyncClient, session, auth_user_and_token):
    """Endorsing a non-existent vendor returns 404."""
    _, token = auth_user_and_token

    resp = await client.post(
        "/api/vendors/99999/endorsements",
        json={"vendor_id": 99999, "trust_rating": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Integration tests: Vendor field update (PATCH)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vendor_field_update(client: AsyncClient, session, auth_user_and_token):
    """PATCH /api/vendors/{id} updates allowed fields and creates audit log."""
    from models.bids import Vendor
    from models.auth import AuditLog
    from sqlmodel import select

    user, token = auth_user_and_token

    vendor = Vendor(name="Editable Vendor", phone="+1-555-0000")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    resp = await client.patch(
        f"/api/vendors/{vendor.id}",
        json={
            "phone": "+1-555-9999",
            "vendor_type": "broker",
            "contact_name": "New Contact",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "updated"
    assert data["changes"]["phone"] == "+1-555-9999"
    assert data["changes"]["vendor_type"] == "broker"

    # Verify audit log was created
    result = await session.exec(
        select(AuditLog).where(
            AuditLog.resource_type == "vendor",
            AuditLog.resource_id == str(vendor.id),
        )
    )
    audit = result.first()
    assert audit is not None
    assert audit.action == "vendor.update"


@pytest.mark.asyncio
async def test_vendor_field_update_no_changes(client: AsyncClient, session, auth_user_and_token):
    """PATCH with identical values returns no_changes."""
    from models.bids import Vendor

    user, token = auth_user_and_token

    vendor = Vendor(name="Same Vendor", phone="+1-555-0000")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    resp = await client.patch(
        f"/api/vendors/{vendor.id}",
        json={"phone": "+1-555-0000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_changes"


# ---------------------------------------------------------------------------
# Unit tests: Agent prompt QueryProfile
# ---------------------------------------------------------------------------

class TestAgentPromptQueryProfile:
    def test_prompt_contains_query_profile_fields(self):
        from sourcing.agent import AGENT_SYSTEM_PROMPT
        assert "location_sensitivity" in AGENT_SYSTEM_PROMPT
        assert "transaction_mode" in AGENT_SYSTEM_PROMPT
        assert "contact_priority" in AGENT_SYSTEM_PROMPT
        assert "source_preference" in AGENT_SYSTEM_PROMPT

    def test_prompt_contains_brokered_deal_guidance(self):
        from sourcing.agent import AGENT_SYSTEM_PROMPT
        assert "brokered_deal" in AGENT_SYSTEM_PROMPT
        assert "BROKERED" in AGENT_SYSTEM_PROMPT

    def test_search_web_description_commercial(self):
        from sourcing.tools import SEARCH_WEB
        desc = SEARCH_WEB["description"]
        assert "BUY" in desc or "buy" in desc.lower()
        assert "article" in desc.lower() or "listicle" in desc.lower()
        assert "editorial" not in desc.lower()
