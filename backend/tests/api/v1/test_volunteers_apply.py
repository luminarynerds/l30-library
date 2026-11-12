# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for POST /volunteers/apply.

The public /volunteer/apply page (PR #1022) sends
{first_name, last_name, email, phone, interests, skills, why_volunteer,
background_check_consent, availability} but the endpoint forwarded the raw
dict into VolunteerApplication(**data), whose columns are
{preferred_roles, preferred_days, availability_hours_per_week, ...}.
Every real submission 500'd with
TypeError: 'first_name' is an invalid keyword argument.
"""

import pytest

FORM_PAYLOAD = {
    "first_name": "Sam",
    "last_name": "Calder",
    "email": "sam@example.org",
    "phone": "555-0100",
    "address": "123 Main St",
    "interests": ["Shelving & Sorting", "Tech Help"],
    "skills": ["Spanish", "teaching"],
    "why_volunteer": "I want to help.",
    "background_check_consent": True,
    "availability": "Weekday mornings; Evenings",
}


async def _post_apply(user, db, payload):
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.dependencies import require_authenticated
    from app.core.database import get_db
    from app.main import app

    async def override_user():
        return user

    async def override_db():
        yield db

    app.dependency_overrides[require_authenticated] = override_user
    app.dependency_overrides[get_db] = override_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.post("/api/v1/volunteers/apply", json=payload)
    finally:
        app.dependency_overrides.pop(require_authenticated, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_apply_accepts_public_form_payload(test_db, test_patron):
    """The exact payload the /volunteer/apply page sends must create a draft."""
    response = await _post_apply(test_patron, test_db, FORM_PAYLOAD)
    assert response.status_code == 201, (
        f"apply must accept the public form payload; got {response.status_code}: {response.text}"
    )

    from sqlalchemy import select
    from app.models.volunteer import VolunteerApplication

    result = await test_db.execute(
        select(VolunteerApplication).where(VolunteerApplication.id == response.json()["id"])
    )
    application = result.scalar_one()
    # Interests are mapped to VolunteerRoleCategory values: approval feeds
    # preferred_roles[0] into a DB enum column.
    assert application.preferred_roles == ["shelving", "tech_support"]
    assert application.preferred_days == ["Weekday mornings", "Evenings"]
    assert application.background_check_consent is True
    # Contact/skills/original labels have no columns; they must survive in
    # the reviewer-visible text.
    assert "555-0100" in application.why_volunteer
    assert "Spanish" in application.why_volunteer
    assert "Shelving & Sorting" in application.why_volunteer
    assert "I want to help." in application.why_volunteer


@pytest.mark.asyncio
async def test_apply_rejects_missing_required_fields(test_db, test_patron):
    """Missing why_volunteer/consent must be a 422, not a 500."""
    response = await _post_apply(test_patron, test_db, {"interests": []})
    assert response.status_code == 422, (
        f"invalid payload must 422; got {response.status_code}: {response.text}"
    )


async def _post_review(staff_user, db, application_id, body):
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.auth import get_current_user
    from app.api.v1.dependencies import require_staff
    from app.core.database import get_db
    from app.main import app

    async def override_user():
        return staff_user

    async def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[require_staff] = override_user
    app.dependency_overrides[get_db] = override_db
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            return await ac.post(
                f"/api/v1/volunteers/applications/{application_id}/review",
                json=body,
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_staff, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_review_approve_reads_json_body(test_db, test_patron, test_admin):
    """The staff UI sends {status} in the JSON body; approve must 200 and
    create the volunteer profile (it 422'd when status was a query param)."""
    apply_response = await _post_apply(test_patron, test_db, FORM_PAYLOAD)
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = await _post_review(test_admin, test_db, application_id, {"status": "approved"})
    assert response.status_code == 200, (
        f"approve must accept JSON body; got {response.status_code}: {response.text}"
    )
    assert response.json()["volunteer_id"]


@pytest.mark.asyncio
async def test_review_invalid_status_is_400(test_db, test_patron, test_admin):
    """A status outside the enum must 400 (was a 500 via shadowed fastapi.status)."""
    apply_response = await _post_apply(test_patron, test_db, FORM_PAYLOAD)
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = await _post_review(test_admin, test_db, application_id, {"status": "not-a-status"})
    assert response.status_code == 400, (
        f"invalid status must 400; got {response.status_code}: {response.text}"
    )
