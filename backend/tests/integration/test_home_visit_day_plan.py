# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the home-visit day-plan (map + access-notes).

Covers:
  1. Geocode cache hit returns cached lat/lng without hitting Nominatim.
  2. Nominatim failure leaves the visit with NULL lat/lng + warning;
     no 500 propagates to the response.
  3. OSRM is mocked out -- compute_leg falls back to haversine when the
     mock returns None, and the leg's provider is tagged accordingly.
  4. Day-plan endpoint scopes by current_user.id (visitor scoping).
  5. ``day_plan_sort_index`` survives a re-query (manual sort override).
  6. ``home_visit_access_notes`` is 1:1 with patron -- creating a new
     visit for the same patron does not duplicate the notes row.
  7. Feature flag OFF returns 404 (not 403) so the surface is invisible.

Feature flag ``home_visit_day_plan_enabled`` is patched ON inside each
test (default OFF in fresh DBs).
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.parent_onboarding import (
    HomeVisitAccessNotes, HomeVisitGeocodeCache, HomeVisitPurpose,
    HomeVisitStatus, ParentHomeVisit,
)
from app.models.user import User, UserRole


async def _make_visit(
    db,
    *,
    patron_id: int,
    visitor_id: int,
    scheduled_date: date,
    scheduled_time: str = "09:30",
    address: str | None = "123 Main St, Springfield, OH",
    geocoded_lat: float | None = None,
    geocoded_lng: float | None = None,
    day_plan_sort_index: int | None = None,
) -> ParentHomeVisit:
    visit = ParentHomeVisit(
        patron_id=patron_id,
        visitor_id=visitor_id,
        purpose=HomeVisitPurpose.intake,
        status=HomeVisitStatus.scheduled,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        address=address,
        geocoded_lat=geocoded_lat,
        geocoded_lng=geocoded_lng,
        day_plan_sort_index=day_plan_sort_index,
        follow_up_needed=False,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@pytest.fixture
def flag_on():
    """Patch OrganizationFeaturesService.is_feature_enabled to return True."""
    from app.services.organization_features_service import OrganizationFeaturesService
    with patch.object(
        OrganizationFeaturesService, "is_feature_enabled",
        new=AsyncMock(return_value=True),
    ):
        yield


# --- 1. geocode cache hit ------------------------------------------------

@pytest.mark.integration
async def test_geocode_cache_hit_skips_nominatim(test_db):
    """A cached address must not hit Nominatim a second time."""
    from app.services import home_visit_day_plan_service

    # Seed the cache.
    address = "999 Cache Ln"
    cache_row = HomeVisitGeocodeCache(
        address_hash=home_visit_day_plan_service._hash_address(address),
        address_raw=address,
        lat=12.34,
        lng=56.78,
        provider="nominatim",
        geocoded_at=datetime.now(timezone.utc),
    )
    test_db.add(cache_row)
    await test_db.commit()

    with patch.object(
        home_visit_day_plan_service, "_nominatim_lookup",
        new=AsyncMock(return_value=(0.0, 0.0)),
    ) as nom_mock:
        coords = await home_visit_day_plan_service.get_or_geocode_address(
            test_db, address
        )

    assert coords == (12.34, 56.78)
    nom_mock.assert_not_called()


# --- 2. nominatim failure does not 500 ------------------------------------

@pytest.mark.integration
async def test_nominatim_failure_returns_none_no_raise(test_db):
    """Public Nominatim down / 503 returns None; no exception propagates."""
    from app.services import home_visit_day_plan_service

    with patch.object(
        home_visit_day_plan_service, "_nominatim_lookup",
        new=AsyncMock(return_value=None),
    ):
        coords = await home_visit_day_plan_service.get_or_geocode_address(
            test_db, "uncached address"
        )

    assert coords is None
    # Cache must NOT have been seeded with a fake value.
    from sqlalchemy import select
    row = (
        await test_db.execute(
            select(HomeVisitGeocodeCache)
            .where(HomeVisitGeocodeCache.address_raw == "uncached address")
        )
    ).scalar_one_or_none()
    assert row is None


# --- 3. OSRM unreachable -> haversine fallback ----------------------------

@pytest.mark.integration
async def test_osrm_unreachable_falls_back_to_haversine():
    """When OSRM returns None, compute_leg must return a 'haversine' leg."""
    from app.services import home_visit_day_plan_service

    with patch.object(
        home_visit_day_plan_service, "_osrm_route",
        new=AsyncMock(return_value=None),
    ):
        leg = await home_visit_day_plan_service.compute_leg(
            39.91, -83.81, 39.92, -83.83,
        )

    assert leg.provider == "haversine"
    # Coordinates are ~1.5 km apart; conservative urban drive estimate.
    assert leg.distance_km > 0
    assert leg.drive_minutes >= 1
    assert leg.walk_minutes >= 1


# --- 4. day-plan endpoint scopes by current_user.id ----------------------

@pytest.mark.integration
async def test_day_plan_endpoint_scopes_by_current_user(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """Day plan must only include visits where visitor_id == current_user.id."""
    today = date.today()

    # One visit assigned to the staff member (should show up).
    mine = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        scheduled_date=today,
        scheduled_time="09:00",
        geocoded_lat=39.91, geocoded_lng=-83.81,
    )
    # One visit assigned to someone else (must NOT show up). visitor_id
    # FKs to users.id, so this needs a real second staff user, not a
    # made-up numeric offset.
    other_staff = User(
        email="other-visitor@test.local",
        password_hash="hashed",
        first_name="Other",
        last_name="Visitor",
        role=UserRole.STAFF,
        is_active=True,
    )
    test_db.add(other_staff)
    await test_db.commit()
    await test_db.refresh(other_staff)

    other_visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=other_staff.id,
        scheduled_date=today,
        scheduled_time="10:00",
        geocoded_lat=39.92, geocoded_lng=-83.82,
    )

    response = await staff_client.get(
        "/api/v1/parent-onboarding/home-visits/day-plan",
        params={"date": today.isoformat()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    visit_ids = [s["visit_id"] for s in body["stops"]]
    assert mine.id in visit_ids
    assert other_visit.id not in visit_ids


# --- 5. manual sort override survives a re-query ------------------------

@pytest.mark.integration
async def test_manual_sort_override_survives_requery(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """PATCH /day-plan-sort persists day_plan_sort_index across requests."""
    today = date.today()
    visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        scheduled_date=today,
        scheduled_time="10:00",
        geocoded_lat=39.91, geocoded_lng=-83.81,
    )

    patch_resp = await staff_client.patch(
        f"/api/v1/parent-onboarding/home-visits/{visit.id}/day-plan-sort",
        json={"sort_index": 1},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    # Re-query a fresh day plan and assert the manual_order flag is set.
    plan_resp = await staff_client.get(
        "/api/v1/parent-onboarding/home-visits/day-plan",
        params={"date": today.isoformat()},
    )
    assert plan_resp.status_code == 200
    body = plan_resp.json()
    matching = [s for s in body["stops"] if s["visit_id"] == visit.id]
    assert len(matching) == 1
    assert matching[0]["manual_order"] is True


# --- 6. access notes are 1:1 with patron ---------------------------------

@pytest.mark.integration
async def test_access_notes_are_one_per_patron_not_per_visit(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """Two visits to the same patron share one access_notes row."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    await _make_visit(
        test_db, patron_id=test_patron.id, visitor_id=test_staff.id,
        scheduled_date=today, scheduled_time="09:00",
    )
    await _make_visit(
        test_db, patron_id=test_patron.id, visitor_id=test_staff.id,
        scheduled_date=tomorrow, scheduled_time="11:00",
    )

    # PUT once with the dog flag set.
    put_resp = await staff_client.put(
        f"/api/v1/parent-onboarding/home-visit-access-notes/{test_patron.id}",
        json={"dog_on_premises": True, "dog_safety_note": "friendly, in crate"},
    )
    assert put_resp.status_code == 200, put_resp.text

    # GET returns the same row.
    get_resp = await staff_client.get(
        f"/api/v1/parent-onboarding/home-visit-access-notes/{test_patron.id}",
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["dog_on_premises"] is True

    # And there's exactly ONE row in the table for this patron.
    from sqlalchemy import select, func
    count = (
        await test_db.execute(
            select(func.count(HomeVisitAccessNotes.id))
            .where(HomeVisitAccessNotes.patron_id == test_patron.id)
        )
    ).scalar()
    assert count == 1


# --- 7. flag off => 404 (not 403) ----------------------------------------

@pytest.mark.integration
async def test_day_plan_404_when_flag_off(
    staff_client, test_db, test_patron, test_staff,
):
    """Flag off => 404. The surface must be invisible, not forbidden."""
    today = date.today()
    response = await staff_client.get(
        "/api/v1/parent-onboarding/home-visits/day-plan",
        params={"date": today.isoformat()},
    )
    assert response.status_code == 404, response.text
