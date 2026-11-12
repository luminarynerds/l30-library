# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the lone-worker home-visit safety mechanic.

Covers the four success/edge cases called out in the PR scope:

  1. ``POST /home-visits/{id}/safety-checkin`` happy path - stamps
     ``safety_checkin_at`` + ``safety_checkout_due_at``.
  2. ``POST /home-visits/{id}/safety-checkout`` happy path - stamps
     ``safety_checkout_at``.
  3. Periodic scan flags an overdue visit and would-notify the buddy
     + supervisors (real Resend HTTP call patched so the test does not
     hit the network).
  4. Check-in on a visit with no ``safety_buddy_user_id`` succeeds but
     surfaces a ``buddy_warning`` string.

Feature flag ``home_visit_safety_enabled`` is patched ON inside each
test because the default is OFF (per PR design); we do not want the
test suite to depend on a fresh DB seed having the flag flipped.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.parent_onboarding import (
    HomeVisitPurpose, HomeVisitStatus, ParentHomeVisit,
)
from app.models.user import UserRole
from app.services.home_visit_safety_tasks import scan_and_notify_overdue_visits


# --- helpers --------------------------------------------------------------

async def _make_visit(
    db,
    *,
    patron_id: int,
    visitor_id: int,
    safety_buddy_user_id: int | None = None,
    safety_checkin_at: datetime | None = None,
    safety_checkout_due_at: datetime | None = None,
    safety_overdue_flagged_at: datetime | None = None,
    scheduled_date: date | None = None,
) -> ParentHomeVisit:
    visit = ParentHomeVisit(
        patron_id=patron_id,
        visitor_id=visitor_id,
        purpose=HomeVisitPurpose.intake,
        status=HomeVisitStatus.scheduled,
        scheduled_date=scheduled_date or (date.today() + timedelta(days=1)),
        scheduled_time="14:00",
        address="42 Sample Ln",
        safety_buddy_user_id=safety_buddy_user_id,
        safety_checkin_at=safety_checkin_at,
        safety_checkout_due_at=safety_checkout_due_at,
        safety_overdue_flagged_at=safety_overdue_flagged_at,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@pytest.fixture
def flag_on():
    """Patch OrganizationFeaturesService.is_feature_enabled to return True.

    Two patch sites because the route guard and the scan task import the
    service from different module paths -- so a single patch leaves one
    branch unmocked. (See L30 [[feedback_l30_grep_callers_before_path_a_vs_b]].)
    """
    from app.services.organization_features_service import OrganizationFeaturesService
    with patch.object(
        OrganizationFeaturesService, "is_feature_enabled",
        new=AsyncMock(return_value=True),
    ):
        yield


# --- 1. check-in happy path ----------------------------------------------

@pytest.mark.integration
async def test_safety_checkin_stamps_checkin_and_due_at(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """POST /safety-checkin stamps both checkin time and due-at deadline."""
    buddy = test_staff  # any user works as buddy here; staff doubles up
    visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        safety_buddy_user_id=buddy.id,
    )
    before = datetime.now(timezone.utc)

    response = await staff_client.post(
        f"/api/v1/parent-onboarding/home-visits/{visit.id}/safety-checkin",
        json={"visit_duration_minutes": 60},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["visit_id"] == visit.id
    assert body["safety_checkin_at"] is not None
    assert body["safety_checkout_due_at"] is not None
    # No warning expected with a buddy assigned.
    assert body["buddy_warning"] is None

    # sqlite's DateTime(timezone=True) returns naive datetimes on round-trip,
    # so normalize both sides before comparing.
    def _naive(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    checkin = _naive(datetime.fromisoformat(body["safety_checkin_at"].replace("Z", "+00:00")))
    due_at = _naive(datetime.fromisoformat(body["safety_checkout_due_at"].replace("Z", "+00:00")))
    before_naive = _naive(before)
    # Allow 5s slack for clock drift between the test process and the DB.
    assert checkin >= before_naive - timedelta(seconds=5)
    # 60 visit + 15 grace = 75 minutes; due_at should be ~75 min after checkin.
    delta = (due_at - checkin).total_seconds() / 60.0
    assert 74.5 <= delta <= 75.5, f"expected ~75 min, got {delta}"


# --- 2. check-out happy path ---------------------------------------------

@pytest.mark.integration
async def test_safety_checkout_stamps_checkout(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """POST /safety-checkout sets safety_checkout_at on a checked-in visit."""
    checkin = datetime.now(timezone.utc) - timedelta(minutes=30)
    due = checkin + timedelta(minutes=75)
    visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        safety_buddy_user_id=test_staff.id,
        safety_checkin_at=checkin,
        safety_checkout_due_at=due,
    )

    response = await staff_client.post(
        f"/api/v1/parent-onboarding/home-visits/{visit.id}/safety-checkout",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["safety_checkout_at"] is not None

    # Re-read the row to confirm the DB write took.
    await test_db.refresh(visit)
    assert visit.safety_checkout_at is not None


# --- 3. periodic scan: flag + would-notify -------------------------------

@pytest.mark.integration
async def test_scan_flags_overdue_and_sends_alerts(
    flag_on, test_db, test_patron, test_staff,
):
    """The periodic scan flags an overdue visit and dispatches alerts.

    Patches ``send_email`` (the only outbound network call) so we don't
    hit Resend. Asserts:
      - safety_overdue_flagged_at is now set on the visit.
      - send_email was invoked at least once (buddy + supervisor pool).
      - Subsequent scan does NOT re-notify (idempotency).
    """
    overdue_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    checkin = overdue_at - timedelta(minutes=75)
    visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        safety_buddy_user_id=test_staff.id,
        safety_checkin_at=checkin,
        safety_checkout_due_at=overdue_at,
    )

    with patch(
        "app.services.home_visit_safety_tasks.send_email",
        new=AsyncMock(return_value=True),
    ) as mock_send:
        summary = await scan_and_notify_overdue_visits(test_db)

    assert summary["flagged"] == 1, summary
    assert summary["notified_ok"] >= 1
    assert mock_send.await_count >= 1

    await test_db.refresh(visit)
    assert visit.safety_overdue_flagged_at is not None

    # Second pass: nothing pending now (already flagged).
    with patch(
        "app.services.home_visit_safety_tasks.send_email",
        new=AsyncMock(return_value=True),
    ) as mock_send_again:
        summary2 = await scan_and_notify_overdue_visits(test_db)

    assert summary2["flagged"] == 0
    assert mock_send_again.await_count == 0


# --- 4. no buddy: checkin still works but warns --------------------------

@pytest.mark.integration
async def test_checkin_without_buddy_returns_warning(
    flag_on, staff_client, test_db, test_patron, test_staff,
):
    """A visit with no safety_buddy_user_id can still check-in; the
    response surfaces a buddy_warning string so the UI can toast it."""
    visit = await _make_visit(
        test_db,
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        safety_buddy_user_id=None,
    )

    response = await staff_client.post(
        f"/api/v1/parent-onboarding/home-visits/{visit.id}/safety-checkin",
        json={"visit_duration_minutes": 45},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["safety_buddy_user_id"] is None
    assert body["buddy_warning"], "expected a warning when no buddy is set"
    assert "buddy" in body["buddy_warning"].lower()
