# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Service-layer tests for the childcare authorized-pickup helper.

Exercises ``ChildcareService.validate_pickup_authorization`` directly so we
avoid the FastAPI test-client + httpx + dependency_overrides path that hits
the known pytest-asyncio + SessionMaker fixture-ordering issue on L30
(see test_parent_connection_groups_enrollment_service.py docstring).

Three behaviors covered:
  1. Happy path -- pickup name matches an authorized entry -> returns the
     matched dict (case-insensitive name, exact phone), no override needed.
  2. Unauthorized pickup with no override reason -> raises PickupNotAuthorized
     so the router can translate to 422 with the allowed list in detail.
  3. Legacy registration (no authorized_pickup list) without staff override
     -> raises PickupNotAuthorized; WITH override reason -> returns None to
     signal "checkout proceeds, audit columns populated from request body".
"""
from datetime import date

import pytest

from app.models.parent_onboarding import (
    ChildcareRegistration,
    ChildcareRegistrationStatus,
    ChildcareSession,
    ChildcareSessionStatus,
)
from app.services.parent_onboarding import (
    ChildcareService,
    PickupNotAuthorized,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mk_patron(test_db) -> int:
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email="pickup-parent@example.test",
        password_hash=hash_password("Password123!"),
        first_name="P",
        last_name="One",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u.id


async def _mk_registration(
    test_db, *, patron_id: int, authorized_pickup: list[dict] | None = None
) -> ChildcareRegistration:
    session = ChildcareSession(
        branch_id=1,
        date=date(2026, 6, 1),
        start_time="09:00",
        end_time="12:00",
        max_children=10,
        status=ChildcareSessionStatus.available,
        staff_id=None,
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    reg = ChildcareRegistration(
        session_id=session.id,
        patron_id=patron_id,
        child_name="Test Child",
        child_age_months=24,
        emergency_contact_name="EC Person",
        emergency_contact_phone="5551110000",
        status=ChildcareRegistrationStatus.checked_in,
        authorized_pickup=authorized_pickup if authorized_pickup is not None else [],
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_pickup_authorization_matches_entry(test_db):
    patron_id = await _mk_patron(test_db)
    reg = await _mk_registration(
        test_db,
        patron_id=patron_id,
        authorized_pickup=[
            {"name": "Aunt Jo", "phone": "5552223333",
             "relationship": "aunt", "id_required": True},
            {"name": "Grandma Lin", "phone": "5554445555",
             "relationship": "grandparent", "id_required": False},
        ],
    )

    # Name match is case-insensitive; phone must equal exactly.
    matched = ChildcareService.validate_pickup_authorization(
        reg, picked_up_by_name="aunt jo", picked_up_by_phone="5552223333",
        staff_override_reason=None,
    )
    assert matched is not None
    assert matched["name"] == "Aunt Jo"
    assert matched["phone"] == "5552223333"


@pytest.mark.asyncio
async def test_validate_pickup_authorization_rejects_unauthorized(test_db):
    patron_id = await _mk_patron(test_db)
    reg = await _mk_registration(
        test_db,
        patron_id=patron_id,
        authorized_pickup=[
            {"name": "Aunt Jo", "phone": "5552223333",
             "relationship": "aunt", "id_required": True},
        ],
    )

    with pytest.raises(PickupNotAuthorized) as exc:
        ChildcareService.validate_pickup_authorization(
            reg,
            picked_up_by_name="Random Stranger",
            picked_up_by_phone="5550000000",
            staff_override_reason=None,
        )
    # detail must enumerate the authorized names so staff sees who IS allowed
    assert "Aunt Jo" in exc.value.detail
    assert exc.value.has_authorized_list is True


@pytest.mark.asyncio
async def test_validate_pickup_authorization_legacy_registration_fallback(test_db):
    """Legacy registration (no list) requires staff_override_reason."""
    patron_id = await _mk_patron(test_db)
    reg = await _mk_registration(test_db, patron_id=patron_id, authorized_pickup=[])

    # Without override -> reject (with hint that no list is on file)
    with pytest.raises(PickupNotAuthorized) as exc:
        ChildcareService.validate_pickup_authorization(
            reg,
            picked_up_by_name="Anyone",
            picked_up_by_phone="5550000000",
            staff_override_reason=None,
        )
    assert exc.value.has_authorized_list is False

    # With override -> returns None (caller must populate audit columns from
    # the request body); no exception raised.
    matched = ChildcareService.validate_pickup_authorization(
        reg,
        picked_up_by_name="Anyone",
        picked_up_by_phone="5550000000",
        staff_override_reason="Parent verbally authorized at desk",
    )
    assert matched is None
