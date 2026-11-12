# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: list endpoints must serialize rows whose nullable DB columns
hold NULL but whose response schema declares the field non-Optional with a
default.

Several response schemas (CulturalProgramResponse, PartnerOrganizationResponse,
ImpactStoryResponse, OutreachPartnerResponse, BulkCheckoutResponse +
BulkCheckoutItemResponse, PTORequestResponse, StorytimeSessionResponse,
StaffExpertiseResponse) declare fields like partners_involved/reach_count/
default_deposit_amount/fine_amount/auto_delegate/is_cancelled/
relevant_credentials as non-null with a default, but the backing columns are
nullable and seeded/legacy rows hold NULL. from_attributes hands pydantic the
explicit None, which the declared default does NOT cover, so the GET endpoints
500'd with ResponseValidationError. Each schema now coerces None back to the
field's default at the boundary.

Inserts use raw SQL with inline literals for enum/date/bool columns (Postgres
treats them as `unknown` and assignment-casts to the column type) so the ORM
does not apply its Python-side defaults; only the target columns are left NULL.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.api.v1 import feature_guards
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
async def staff(db):
    user = User(
        email="null-misc-staff@example.com",
        first_name="NullMisc",
        last_name="Staff",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def _override(staff, db):
    """Override get_db + get_current_user (staff) + the feature guards that gate
    the outreach/pto/storytime routers (each raises 404 when its feature toggle
    is off). Immigrant endpoints are anonymous, but these overrides are harmless
    there."""
    async def _db():
        yield db

    async def _staff():
        return staff

    async def _noop():
        return None

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _staff
    app.dependency_overrides[feature_guards.require_outreach_enabled] = _noop
    app.dependency_overrides[feature_guards.require_staff_scheduling_enabled] = _noop
    app.dependency_overrides[feature_guards.require_storytime_enabled] = _noop
    app.state.setup_complete = True
    yield
    for dep in (
        get_db,
        get_current_user,
        feature_guards.require_outreach_enabled,
        feature_guards.require_staff_scheduling_enabled,
        feature_guards.require_storytime_enabled,
    ):
        app.dependency_overrides.pop(dep, None)


def _client():
    from httpx import AsyncClient, ASGITransport

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost")


# ---------------------------------------------------------------------------
# Fixtures: rows with only the target column(s) NULL.
# ---------------------------------------------------------------------------

@pytest.fixture
async def null_cultural_program(db):
    """partners_involved NULL; every other response-required column populated."""
    pid = (await db.execute(text(
        "INSERT INTO cultural_programs "
        "(title, program_type, event_date, is_virtual, is_in_person, "
        " is_family_friendly, registration_required, status, "
        " languages_featured, partners_involved) "
        "VALUES (:t, 'workshop', '2020-01-01', false, true, "
        " true, false, 'planned', '{}', NULL) RETURNING id"
    ), {"t": "Legacy Cultural Program"})).scalar_one()
    await db.commit()
    return pid


@pytest.fixture
async def null_partner_org(db):
    """volunteer_hours_contributed NULL; other required columns populated."""
    oid = (await db.execute(text(
        "INSERT INTO partner_organizations "
        "(name, primary_email, status, annual_collaborations, "
        " languages_served, services_offered, target_populations, "
        " service_area, shared_programs, volunteer_hours_contributed) "
        "VALUES (:n, :e, 'active', 0, "
        " '{}', '{}', '{}', '{}', '{}', NULL) RETURNING id"
    ), {"n": "Legacy Partner Org", "e": "partner@example.com"})).scalar_one()
    await db.commit()
    return oid


@pytest.fixture
async def null_impact_story(db):
    """reach_count NULL; other required columns populated."""
    sid = (await db.execute(text(
        "INSERT INTO impact_stories "
        "(title, full_story, submitted_date, status, featured_on_website, "
        " featured_on_social_media, language, themes, consent_to_publish, "
        " consent_to_attribute, reach_count) "
        "VALUES (:t, :f, '2020-01-01', 'submitted', false, "
        " false, 'english', '{}', false, false, NULL) RETURNING id"
    ), {"t": "Legacy Impact Story", "f": "Once upon a time."})).scalar_one()
    await db.commit()
    return sid


@pytest.fixture
async def null_outreach_partner(db):
    """default_deposit_amount / checkout_limit / loan_period_days / tags /
    custom_fields all NULL; other required columns populated."""
    pid = (await db.execute(text(
        "INSERT INTO outreach_partners "
        "(name, partner_type, status, partnership_tier, "
        " allows_bulk_checkout, allows_institutional_card, requires_deposit, "
        " default_deposit_amount, checkout_limit, loan_period_days, "
        " tags, custom_fields) "
        "VALUES (:n, 'school', 'active', 'bronze', "
        " true, true, false, "
        " NULL, NULL, NULL, NULL, NULL) RETURNING id"
    ), {"n": "Legacy Outreach Partner"})).scalar_one()
    await db.commit()
    return pid


@pytest.fixture
async def null_bulk_checkout(db, null_outreach_partner):
    """BulkCheckout with deposit_amount + format_preferences NULL, plus a child
    BulkCheckoutItem with fine_amount NULL. total_items/items_returned/items_lost
    set to 0 so the endpoint's items_outstanding subtraction does not hit None."""
    cid = (await db.execute(text(
        "INSERT INTO bulk_checkouts "
        "(partner_id, checkout_name, status, requestor_name, "
        " checkout_date, due_date, total_items, items_returned, items_lost, "
        " items_damaged, deposit_required, deposit_collected, topic_requests, "
        " deposit_amount, format_preferences) "
        "VALUES (:pid, :cn, 'active', :rn, "
        " '2020-01-01', '2020-12-31', 0, 0, 0, "
        " 0, false, false, '[]'::jsonb, "
        " NULL, NULL) RETURNING id"
    ), {"pid": null_outreach_partner, "cn": "Legacy Checkout",
        "rn": "Mrs. Legacy"})).scalar_one()
    await db.execute(text(
        "INSERT INTO bulk_checkout_items "
        "(bulk_checkout_id, barcode, status, fine_amount) "
        "VALUES (:cid, :bc, 'checked_out', NULL)"
    ), {"cid": cid, "bc": "BC-LEGACY-1"})
    await db.commit()
    return cid


@pytest.fixture
async def null_pto_request(db, staff):
    """auto_delegate + gradual_return_enabled NULL; user_id = the overridden
    staff user (the list endpoint filters by current user)."""
    rid = (await db.execute(text(
        "INSERT INTO pto_requests "
        "(user_id, start_date, end_date, pto_type, status, partial_day_type, "
        " auto_delegate, gradual_return_enabled) "
        "VALUES (:uid, '2020-06-01', '2020-06-05', 'vacation', 'submitted', "
        " 'full_day', NULL, NULL) RETURNING id"
    ), {"uid": staff.id})).scalar_one()
    await db.commit()
    return rid


@pytest.fixture
async def null_storytime_session(db):
    """is_cancelled NULL; needs a storytime_series parent."""
    series_id = (await db.execute(text(
        "INSERT INTO storytime_series "
        "(title, series_type, primary_age_group, secondary_age_groups, "
        " location, duration_minutes, secondary_leader_ids, is_active) "
        "VALUES (:t, 'weekly', 'toddlers', '{}', "
        " 'Storytime Room', 30, '{}', true) RETURNING id"
    ), {"t": "Legacy Series"})).scalar_one()
    sid = (await db.execute(text(
        "INSERT INTO storytime_sessions "
        "(series_id, session_date, start_time, status, book_ids, "
        " expected_attendance, actual_attendance, is_cancelled) "
        "VALUES (:sid, '2020-01-01', '2020-01-01 10:00:00+00', 'scheduled', "
        " '{}', 0, 0, NULL) RETURNING id"
    ), {"sid": series_id})).scalar_one()
    await db.commit()
    return sid


@pytest.fixture
async def null_staff_expertise(db, staff):
    """relevant_credentials NULL; is_public true so the search endpoint returns
    it; staff_id = a real user."""
    eid = (await db.execute(text(
        "INSERT INTO staff_expertise "
        "(staff_id, organization_id, domain, level, willing_to_mentor, "
        " willing_to_train, willing_to_consult, is_public, relevant_credentials) "
        "VALUES (:uid, 1, :d, 'proficient', false, "
        " false, true, true, NULL) RETURNING id"
    ), {"uid": staff.id, "d": "legacy cataloging"})).scalar_one()
    await db.commit()
    return eid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cultural_programs_list_null_partners(_override, null_cultural_program):
    async with _client() as ac:
        resp = await ac.get("/api/v1/immigrant-services/cultural-programs")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["items"] if r["id"] == null_cultural_program)
    assert row["partners_involved"] == []


@pytest.mark.asyncio
async def test_partner_organizations_list_null_volunteer_hours(_override, null_partner_org):
    async with _client() as ac:
        resp = await ac.get("/api/v1/immigrant-services/partner-organizations")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["items"] if r["id"] == null_partner_org)
    assert row["volunteer_hours_contributed"] == 0.0


@pytest.mark.asyncio
async def test_impact_stories_list_null_reach_count(_override, null_impact_story):
    async with _client() as ac:
        resp = await ac.get("/api/v1/immigrant-services/impact-stories")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["items"] if r["id"] == null_impact_story)
    assert row["reach_count"] == 0


@pytest.mark.asyncio
async def test_outreach_partners_list_null_fields(_override, null_outreach_partner):
    async with _client() as ac:
        resp = await ac.get("/api/v1/outreach/partners")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["partners"] if r["id"] == null_outreach_partner)
    assert row["default_deposit_amount"] == 0.0
    assert row["checkout_limit"] == 0
    assert row["loan_period_days"] == 0
    assert row["tags"] == []
    assert row["custom_fields"] == {}


@pytest.mark.asyncio
async def test_bulk_checkouts_list_null_fields(_override, null_bulk_checkout):
    async with _client() as ac:
        resp = await ac.get("/api/v1/outreach/bulk-checkouts")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["checkouts"] if r["id"] == null_bulk_checkout)
    assert row["deposit_amount"] == 0.0
    assert row["format_preferences"] == []
    # nested item: fine_amount coerced from NULL
    assert len(row["items"]) == 1
    assert row["items"][0]["fine_amount"] == 0.0


@pytest.mark.asyncio
async def test_pto_requests_list_null_bools(_override, null_pto_request):
    async with _client() as ac:
        resp = await ac.get("/api/v1/pto/requests")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == null_pto_request)
    assert row["auto_delegate"] is False
    assert row["gradual_return_enabled"] is True


@pytest.mark.asyncio
async def test_storytime_sessions_list_null_is_cancelled(_override, null_storytime_session):
    async with _client() as ac:
        resp = await ac.get("/api/v1/storytime/sessions")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == null_storytime_session)
    assert row["is_cancelled"] is False


@pytest.mark.asyncio
async def test_expertise_list_null_credentials(_override, null_staff_expertise):
    async with _client() as ac:
        resp = await ac.get("/api/v1/professional-judgment/expertise")
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json() if r["id"] == null_staff_expertise)
    assert row["relevant_credentials"] == []
