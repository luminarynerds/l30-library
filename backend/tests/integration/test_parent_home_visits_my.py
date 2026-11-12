# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for GET /api/v1/parent-onboarding/home-visits/my.

This endpoint backs the staff-side `ParentHomeVisitsPage` ("My Home
Visits"). It returns home visits assigned to the current authenticated
user as the *visitor* - the staff member doing the visit - not the
patron being visited.

Without this route the staff page 404s at runtime; before this PR it
was the only home-visit URL in the frontend with no backend handler.

Covered cases:

  - happy path: returns only visits where ``visitor_id == current_user.id``
  - cross-user isolation: another staff's visits are filtered out
  - status filter: ``?status=scheduled`` narrows correctly
  - pagination: ``limit`` + ``offset`` slice deterministically
  - empty result: returns 0/[] not 404 when user has no visits
  - unauth: 401 when no auth dependency is overridden
  - literal path beats param route: ``/my`` does not collide with
    ``/{visit_id}`` (was a real risk; FastAPI matches in registration
    order, so the literal must be declared first - see route docstring)
"""
from datetime import date, timedelta

import pytest

from app.core.security import hash_password
from app.models.parent_onboarding import (
    HomeVisitPurpose, HomeVisitStatus, ParentHomeVisit,
)
from app.models.user import User, UserRole


@pytest.fixture
async def other_staff(test_db):
    """A second staff user, to verify cross-visitor isolation."""
    user = User(
        email="other_staff@example.com",
        password_hash=hash_password("OtherStaff123!"),
        first_name="Other",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _make_visit(
    db,
    *,
    patron_id: int,
    visitor_id: int,
    status: HomeVisitStatus = HomeVisitStatus.scheduled,
    scheduled_date: date | None = None,
    purpose: HomeVisitPurpose = HomeVisitPurpose.intake,
) -> ParentHomeVisit:
    visit = ParentHomeVisit(
        patron_id=patron_id,
        visitor_id=visitor_id,
        purpose=purpose,
        status=status,
        scheduled_date=scheduled_date or (date.today() + timedelta(days=7)),
        scheduled_time="14:30",
        address="123 Test Lane",
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@pytest.mark.integration
class TestListMyHomeVisits:
    """GET /api/v1/parent-onboarding/home-visits/my"""

    async def test_returns_only_my_visits(
        self, staff_client, test_db, test_patron, test_staff, other_staff,
    ):
        """Only visits where ``visitor_id == current_user.id`` are returned."""
        mine_a = await _make_visit(test_db, patron_id=test_patron.id, visitor_id=test_staff.id)
        mine_b = await _make_visit(
            test_db,
            patron_id=test_patron.id,
            visitor_id=test_staff.id,
            scheduled_date=date.today() + timedelta(days=14),
        )
        # A visit assigned to a different visitor - must not leak.
        await _make_visit(test_db, patron_id=test_patron.id, visitor_id=other_staff.id)

        response = await staff_client.get("/api/v1/parent-onboarding/home-visits/my")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2, body
        visit_ids = {v["id"] for v in body["visits"]}
        assert visit_ids == {mine_a.id, mine_b.id}
        # Sanity: every row really is mine.
        for v in body["visits"]:
            assert v["visitor_id"] == test_staff.id

    async def test_empty_when_user_has_no_visits(
        self, staff_client, test_db, test_patron, other_staff,
    ):
        """User with no assigned visits gets a 200 + empty list, not a 404."""
        await _make_visit(test_db, patron_id=test_patron.id, visitor_id=other_staff.id)

        response = await staff_client.get("/api/v1/parent-onboarding/home-visits/my")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body == {
            "visits": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }

    async def test_status_filter(
        self, staff_client, test_db, test_patron, test_staff,
    ):
        """``?status=completed`` returns only completed visits."""
        scheduled = await _make_visit(
            test_db, patron_id=test_patron.id, visitor_id=test_staff.id,
            status=HomeVisitStatus.scheduled,
        )
        completed = await _make_visit(
            test_db, patron_id=test_patron.id, visitor_id=test_staff.id,
            status=HomeVisitStatus.completed,
            scheduled_date=date.today() - timedelta(days=3),
        )

        response = await staff_client.get(
            "/api/v1/parent-onboarding/home-visits/my?status=completed"
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["visits"][0]["id"] == completed.id
        assert body["visits"][0]["status"] == "completed"
        # And the scheduled one is genuinely excluded.
        assert all(v["id"] != scheduled.id for v in body["visits"])

    async def test_pagination(
        self, staff_client, test_db, test_patron, test_staff,
    ):
        """``limit`` + ``offset`` produce deterministic, non-overlapping slices."""
        # Three visits across different dates; service orders by scheduled_date desc.
        for i in range(3):
            await _make_visit(
                test_db,
                patron_id=test_patron.id,
                visitor_id=test_staff.id,
                scheduled_date=date.today() + timedelta(days=7 + i),
            )

        page1 = await staff_client.get(
            "/api/v1/parent-onboarding/home-visits/my?limit=2&offset=0"
        )
        page2 = await staff_client.get(
            "/api/v1/parent-onboarding/home-visits/my?limit=2&offset=2"
        )

        assert page1.status_code == 200, page1.text
        assert page2.status_code == 200, page2.text
        body1, body2 = page1.json(), page2.json()
        assert body1["total"] == body2["total"] == 3
        assert len(body1["visits"]) == 2
        assert len(body2["visits"]) == 1
        ids1 = {v["id"] for v in body1["visits"]}
        ids2 = {v["id"] for v in body2["visits"]}
        assert ids1.isdisjoint(ids2), "page1 and page2 overlap"

    async def test_literal_path_not_shadowed_by_visit_id(
        self, staff_client, test_db, test_patron, test_staff,
    ):
        """``/home-visits/my`` must NOT be matched as ``/home-visits/{visit_id}``.

        Regression guard: if the literal route is ever re-ordered after the
        param route, FastAPI will try to coerce ``"my"`` to int, returning 422.
        This test fails loudly if that ordering breaks.
        """
        await _make_visit(test_db, patron_id=test_patron.id, visitor_id=test_staff.id)

        response = await staff_client.get("/api/v1/parent-onboarding/home-visits/my")

        # If shadowed, response.status_code would be 422 with detail mentioning
        # int parsing of "my". The literal route should match instead and 200.
        assert response.status_code == 200, response.text
        body = response.json()
        # And we get the list shape, not the single-visit shape.
        assert "visits" in body and "total" in body

    async def test_requires_authentication(
        self, public_client, test_db, test_patron, test_staff,
    ):
        """Without an authenticated user, the endpoint refuses to serve."""
        await _make_visit(test_db, patron_id=test_patron.id, visitor_id=test_staff.id)

        response = await public_client.get("/api/v1/parent-onboarding/home-visits/my")

        # require_authenticated raises 401 via get_current_user when no token
        # is present; public_client deliberately doesn't override auth.
        assert response.status_code in (401, 403), response.text
