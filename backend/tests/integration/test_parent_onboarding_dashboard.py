# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for GET /api/v1/parent-onboarding/dashboard.

Regression coverage for the Up Next rail bug (#1880): the dashboard summaries
never carried an owner field, so the rail's `undefined !== currentUserId`
comparisons dropped everything for every coordinator, always. #1880 added
`staff_id` / `coordinator_id` / `visitor_id` to the three summary schemas and
threaded them through the dashboard service, but shipped with zero backend
tests -- this file covers the wire payload directly (assigned + null cases
for all three), which is what the frontend actually consumes.

Session `staff_id` and visit `visitor_id` are optional and never
auto-assigned at creation (unassigned is the common case, not an edge case),
so `null` there must round-trip as an explicit `null` key, not a dropped one
-- the frontend's null-visible-to-everyone rail semantics depend on it.
Assignment `coordinator_id` is required at creation; the null case here only
covers wire-shape correctness (would the field come through if it were ever
null), not "this is the expected common case."
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.parent_onboarding import (
    CareAssignmentStatus,
    CareCoordinatorAssignment,
    HomeVisitPurpose,
    HomeVisitStatus,
    ParentHomeVisit,
    ParentOnboardingSession,
    ParentOnboardingStatus,
    RiskLevel,
)


@pytest.mark.integration
async def test_recent_sessions_include_assigned_staff_id(
    staff_client, test_db, test_patron, test_staff
):
    """A session assigned to a coordinator reports that coordinator's staff_id."""
    session = ParentOnboardingSession(
        patron_id=test_patron.id,
        staff_id=test_staff.id,
        branch_id=1,
        status=ParentOnboardingStatus.scheduled,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(s for s in body["recent_sessions"] if s["id"] == session.id)
    assert match["staff_id"] == test_staff.id


@pytest.mark.integration
async def test_recent_sessions_report_null_staff_id_when_unassigned(
    staff_client, test_db, test_patron
):
    """An unassigned session (staff_id never set) reports staff_id: null,
    not a missing key -- the frontend relies on `staff_id == null` to keep
    unassigned sessions visible to every coordinator."""
    session = ParentOnboardingSession(
        patron_id=test_patron.id,
        staff_id=None,
        branch_id=1,
        status=ParentOnboardingStatus.scheduled,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(s for s in body["recent_sessions"] if s["id"] == session.id)
    assert "staff_id" in match
    assert match["staff_id"] is None


@pytest.mark.integration
async def test_overdue_assignments_include_coordinator_id(
    staff_client, test_db, test_patron, test_staff
):
    """An assignment with no check-ins is "overdue" by definition (see
    ParentOnboardingDashboardService.get_dashboard) and reports its
    coordinator's coordinator_id."""
    assignment = CareCoordinatorAssignment(
        patron_id=test_patron.id,
        coordinator_id=test_staff.id,
        status=CareAssignmentStatus.active,
        risk_level=RiskLevel.medium,
        start_date=date.today() - timedelta(days=7),
    )
    test_db.add(assignment)
    await test_db.commit()
    await test_db.refresh(assignment)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(a for a in body["overdue_assignments"] if a["id"] == assignment.id)
    assert match["coordinator_id"] == test_staff.id


@pytest.mark.integration
async def test_overdue_assignments_report_null_coordinator_id_when_unassigned(
    staff_client, test_db, test_patron
):
    """coordinator_id is required at creation via the API, but the DB column
    is nullable (ON DELETE SET NULL when the coordinator account is
    removed). Confirm the wire shape carries an explicit null rather than
    dropping the key in that state, even though it isn't the common case."""
    assignment = CareCoordinatorAssignment(
        patron_id=test_patron.id,
        coordinator_id=None,
        status=CareAssignmentStatus.active,
        risk_level=RiskLevel.medium,
        start_date=date.today() - timedelta(days=7),
    )
    test_db.add(assignment)
    await test_db.commit()
    await test_db.refresh(assignment)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(a for a in body["overdue_assignments"] if a["id"] == assignment.id)
    assert "coordinator_id" in match
    assert match["coordinator_id"] is None


@pytest.mark.integration
async def test_upcoming_visits_include_visitor_id(
    staff_client, test_db, test_patron, test_staff
):
    """A visit assigned to a coordinator reports that coordinator's visitor_id."""
    visit = ParentHomeVisit(
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        purpose=HomeVisitPurpose.check_in,
        status=HomeVisitStatus.scheduled,
        scheduled_date=date.today() + timedelta(days=1),
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(v for v in body["upcoming_visits"] if v["id"] == visit.id)
    assert match["visitor_id"] == test_staff.id


@pytest.mark.integration
async def test_upcoming_visits_report_null_visitor_id_when_unassigned(
    staff_client, test_db, test_patron
):
    """An unassigned visit (visitor_id never set) reports visitor_id: null,
    not a missing key -- same null-visible-to-everyone reasoning as sessions
    (ParentHomeVisitCreate.visitor_id is optional and never auto-assigned)."""
    visit = ParentHomeVisit(
        patron_id=test_patron.id,
        visitor_id=None,
        purpose=HomeVisitPurpose.check_in,
        status=HomeVisitStatus.scheduled,
        scheduled_date=date.today() + timedelta(days=1),
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    resp = await staff_client.get("/api/v1/parent-onboarding/dashboard")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    match = next(v for v in body["upcoming_visits"] if v["id"] == visit.id)
    assert "visitor_id" in match
    assert match["visitor_id"] is None
