# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Library Outreach Visit lifecycle.

Tests the full lifecycle of outreach visits:
1. Schedule a STORYTIME visit for next Tuesday with Somewhere Up North Elementary
2. Verify OutreachVisit created with status SCHEDULED
3. Complete the visit with attendance/metrics outcomes
4. Verify visit status changes to COMPLETED with all metrics stored
5. Cancel a different scheduled visit and verify CANCELLED status
"""

from datetime import date, datetime, timedelta, timezone

import pytest


def _next_tuesday() -> date:
    """Return the date of next Tuesday from today."""
    today = date.today()
    days_ahead = 1 - today.weekday()  # Monday=0, Tuesday=1
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


# ============ Fixtures ============


@pytest.fixture
async def staff_member(test_db):
    """Create a staff user for outreach visit operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="visit_staff@l30.org",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Moira",
        last_name="Rose",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def schitt_creek_elementary(test_db, staff_member):
    """Create Somewhere Up North Elementary as an outreach partner."""
    from app.models.outreach import OutreachPartner

    partner = OutreachPartner(
        name="Somewhere Up North Elementary",
        partner_type="school",
        status="active",
        address_line1="456 Elm Street",
        city="Somewhere Up North",
        state="CA",
        zip_code="91234",
        primary_contact_name="Jocelyn Schitt",
        primary_contact_email="jschitt@schittcreekelementary.edu",
        primary_contact_phone="555-8765",
        school_level="elementary",
        school_district="Somewhere Up North USD",
        student_count=300,
        teacher_count=18,
        allows_bulk_checkout=True,
        allows_institutional_card=True,
        checkout_limit=150,
        loan_period_days=28,
        created_by_id=staff_member.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


# ============ Visit Lifecycle Tests ============


@pytest.mark.asyncio
async def test_schedule_storytime_visit(test_db, schitt_creek_elementary, staff_member):
    """
    Step 1: Schedule a STORYTIME visit for next Tuesday with Somewhere Up North Elementary.
    Step 2: Verify OutreachVisit created with status SCHEDULED.
    """
    from app.models.outreach import OutreachVisit

    next_tue = _next_tuesday()

    visit = OutreachVisit(
        partner_id=schitt_creek_elementary.id,
        visit_type="storytime",
        status="scheduled",
        title="Storytime at Somewhere Up North Elementary",
        description="Interactive read-aloud session for K-2 students",
        scheduled_date=next_tue,
        scheduled_start_time="10:00",
        scheduled_end_time="11:00",
        location_name="Somewhere Up North Elementary",
        location_room="Library",
        location_address="456 Elm Street, Somewhere Up North, CA 91234",
        expected_attendees=30,
        age_group="children",
        grade_levels=["K", "1", "2"],
        lead_staff_id=staff_member.id,
        materials_needed=["Picture books", "Puppets", "Library card applications"],
        items_to_deliver=50,
        created_by_id=staff_member.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    # Step 2: Verify the visit was created with SCHEDULED status
    assert visit.id is not None
    assert visit.status == "scheduled"
    assert visit.visit_type == "storytime"
    assert visit.partner_id == schitt_creek_elementary.id
    assert visit.scheduled_date == next_tue
    assert visit.title == "Storytime at Somewhere Up North Elementary"
    assert visit.scheduled_start_time == "10:00"
    assert visit.scheduled_end_time == "11:00"
    assert visit.expected_attendees == 30
    assert visit.lead_staff_id == staff_member.id
    assert visit.location_name == "Somewhere Up North Elementary"
    assert visit.items_to_deliver == 50
    assert "K" in visit.grade_levels
    assert "Picture books" in visit.materials_needed


@pytest.mark.asyncio
async def test_complete_visit_with_outcomes(test_db, schitt_creek_elementary, staff_member):
    """
    Step 3: Complete the visit with outcomes.
    Step 4: Verify visit status changes to COMPLETED with all metrics stored.

    Outcomes:
    - Attendance: 25 children
    - New library cards issued: 3
    - Books distributed: 45
    - Rating: 5/5
    """
    from app.models.outreach import OutreachVisit

    next_tue = _next_tuesday()

    # Create a scheduled visit first
    visit = OutreachVisit(
        partner_id=schitt_creek_elementary.id,
        visit_type="storytime",
        status="scheduled",
        title="Storytime at Somewhere Up North Elementary",
        description="Interactive read-aloud session for K-2 students",
        scheduled_date=next_tue,
        scheduled_start_time="10:00",
        scheduled_end_time="11:00",
        location_name="Somewhere Up North Elementary",
        location_room="Library",
        expected_attendees=30,
        age_group="children",
        grade_levels=["K", "1", "2"],
        lead_staff_id=staff_member.id,
        items_to_deliver=50,
        created_by_id=staff_member.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    # Verify it starts as SCHEDULED
    assert visit.status == "scheduled"

    # Step 3: Complete the visit with outcomes
    visit.status = "completed"
    visit.actual_attendees = 25
    visit.new_cards_issued = 3
    visit.items_delivered = 45
    visit.books_checked_out = 45
    visit.partner_rating = 5
    visit.outcome_notes = "Wonderful storytime session! Children were very engaged."
    visit.partner_feedback = "The kids absolutely loved the puppet show portion."
    visit.staff_notes = "Strong interest in summer reading program. Follow up recommended."
    visit.actual_start_time = datetime(
        next_tue.year, next_tue.month, next_tue.day, 10, 0, tzinfo=timezone.utc
    )
    visit.actual_end_time = datetime(
        next_tue.year, next_tue.month, next_tue.day, 11, 0, tzinfo=timezone.utc
    )
    visit.follow_up_needed = True
    visit.follow_up_notes = "Discuss summer reading program enrollment"
    visit.next_visit_date = next_tue + timedelta(days=14)

    await test_db.commit()
    await test_db.refresh(visit)

    # Step 4: Verify COMPLETED status and all metrics
    assert visit.status == "completed"
    assert visit.actual_attendees == 25
    assert visit.new_cards_issued == 3
    assert visit.items_delivered == 45
    assert visit.books_checked_out == 45
    assert visit.partner_rating == 5
    assert visit.outcome_notes is not None
    assert "engaged" in visit.outcome_notes
    assert visit.partner_feedback is not None
    assert "puppet show" in visit.partner_feedback
    assert visit.staff_notes is not None
    assert visit.actual_start_time is not None
    assert visit.actual_end_time is not None
    assert visit.follow_up_needed is True
    assert visit.next_visit_date == next_tue + timedelta(days=14)


@pytest.mark.asyncio
async def test_cancel_scheduled_visit(test_db, schitt_creek_elementary, staff_member):
    """
    Step 5: Cancel a different scheduled visit and verify status changes to CANCELLED.
    """
    from app.models.outreach import OutreachVisit

    # Create a different scheduled visit (a book delivery visit)
    visit_to_cancel = OutreachVisit(
        partner_id=schitt_creek_elementary.id,
        visit_type="book_delivery",
        status="scheduled",
        title="Book Delivery to Somewhere Up North Elementary",
        description="Delivering new collection of chapter books for 3rd-5th graders",
        scheduled_date=_next_tuesday() + timedelta(days=7),
        scheduled_start_time="14:00",
        scheduled_end_time="14:30",
        location_name="Somewhere Up North Elementary",
        location_room="Front Office",
        expected_attendees=2,
        items_to_deliver=30,
        lead_staff_id=staff_member.id,
        created_by_id=staff_member.id,
    )
    test_db.add(visit_to_cancel)
    await test_db.commit()
    await test_db.refresh(visit_to_cancel)

    # Verify the visit starts as SCHEDULED
    assert visit_to_cancel.status == "scheduled"
    assert visit_to_cancel.id is not None

    # Cancel the visit
    visit_to_cancel.status = "cancelled"
    visit_to_cancel.cancellation_reason = "School closed for teacher professional development day"
    visit_to_cancel.cancelled_by_id = staff_member.id
    visit_to_cancel.cancelled_at = datetime.now(timezone.utc)

    await test_db.commit()
    await test_db.refresh(visit_to_cancel)

    # Verify CANCELLED status and cancellation details
    assert visit_to_cancel.status == "cancelled"
    assert visit_to_cancel.cancellation_reason == "School closed for teacher professional development day"
    assert visit_to_cancel.cancelled_by_id == staff_member.id
    assert visit_to_cancel.cancelled_at is not None


@pytest.mark.asyncio
async def test_full_visit_lifecycle_end_to_end(test_db, schitt_creek_elementary, staff_member):
    """
    End-to-end test combining all lifecycle steps:
    1. Schedule a STORYTIME visit for next Tuesday
    2. Verify SCHEDULED status
    3. Complete with outcomes (attendance: 25, cards: 3, books: 45, rating: 5)
    4. Verify COMPLETED with metrics
    5. Schedule and cancel a second visit, verify CANCELLED
    """
    from sqlalchemy import select
    from app.models.outreach import OutreachVisit

    next_tue = _next_tuesday()

    # --- Step 1 & 2: Schedule and verify STORYTIME visit ---
    storytime_visit = OutreachVisit(
        partner_id=schitt_creek_elementary.id,
        visit_type="storytime",
        status="scheduled",
        title="Storytime at Somewhere Up North Elementary",
        description="Weekly storytime for kindergarten and 1st graders",
        scheduled_date=next_tue,
        scheduled_start_time="10:00",
        scheduled_end_time="11:00",
        location_name="Somewhere Up North Elementary",
        location_room="Library",
        expected_attendees=30,
        age_group="children",
        grade_levels=["K", "1"],
        lead_staff_id=staff_member.id,
        items_to_deliver=50,
        created_by_id=staff_member.id,
    )
    test_db.add(storytime_visit)
    await test_db.commit()
    await test_db.refresh(storytime_visit)

    assert storytime_visit.id is not None
    assert storytime_visit.status == "scheduled"
    assert storytime_visit.visit_type == "storytime"
    assert storytime_visit.partner_id == schitt_creek_elementary.id
    assert storytime_visit.scheduled_date == next_tue

    # --- Step 3 & 4: Complete with outcomes and verify ---
    storytime_visit.status = "completed"
    storytime_visit.actual_attendees = 25
    storytime_visit.new_cards_issued = 3
    storytime_visit.items_delivered = 45
    storytime_visit.books_checked_out = 45
    storytime_visit.partner_rating = 5
    storytime_visit.outcome_notes = "Excellent session with 25 enthusiastic children"
    storytime_visit.actual_start_time = datetime(
        next_tue.year, next_tue.month, next_tue.day, 10, 0, tzinfo=timezone.utc
    )
    storytime_visit.actual_end_time = datetime(
        next_tue.year, next_tue.month, next_tue.day, 11, 0, tzinfo=timezone.utc
    )

    await test_db.commit()
    await test_db.refresh(storytime_visit)

    assert storytime_visit.status == "completed"
    assert storytime_visit.actual_attendees == 25
    assert storytime_visit.new_cards_issued == 3
    assert storytime_visit.items_delivered == 45
    assert storytime_visit.books_checked_out == 45
    assert storytime_visit.partner_rating == 5

    # --- Step 5: Schedule and cancel a different visit ---
    workshop_visit = OutreachVisit(
        partner_id=schitt_creek_elementary.id,
        visit_type="workshop",
        status="scheduled",
        title="Library Skills Workshop at Somewhere Up North Elementary",
        description="Teaching students how to use the library catalog",
        scheduled_date=next_tue + timedelta(days=7),
        scheduled_start_time="13:00",
        scheduled_end_time="14:00",
        location_name="Somewhere Up North Elementary",
        location_room="Computer Lab",
        expected_attendees=20,
        lead_staff_id=staff_member.id,
        created_by_id=staff_member.id,
    )
    test_db.add(workshop_visit)
    await test_db.commit()
    await test_db.refresh(workshop_visit)

    assert workshop_visit.status == "scheduled"

    # Cancel it
    workshop_visit.status = "cancelled"
    workshop_visit.cancellation_reason = "Computer lab unavailable due to maintenance"
    workshop_visit.cancelled_by_id = staff_member.id
    workshop_visit.cancelled_at = datetime.now(timezone.utc)

    await test_db.commit()
    await test_db.refresh(workshop_visit)

    assert workshop_visit.status == "cancelled"
    assert workshop_visit.cancellation_reason == "Computer lab unavailable due to maintenance"
    assert workshop_visit.cancelled_by_id == staff_member.id
    assert workshop_visit.cancelled_at is not None

    # --- Final verification: query both visits from DB ---
    result = await test_db.execute(
        select(OutreachVisit)
        .where(OutreachVisit.partner_id == schitt_creek_elementary.id)
        .order_by(OutreachVisit.scheduled_date)
    )
    all_visits = result.scalars().all()
    assert len(all_visits) == 2

    completed_visit = next(v for v in all_visits if v.status == "completed")
    cancelled_visit = next(v for v in all_visits if v.status == "cancelled")

    assert completed_visit.visit_type == "storytime"
    assert completed_visit.actual_attendees == 25
    assert completed_visit.new_cards_issued == 3
    assert completed_visit.books_checked_out == 45
    assert completed_visit.partner_rating == 5

    assert cancelled_visit.visit_type == "workshop"
    assert cancelled_visit.cancellation_reason is not None
    assert cancelled_visit.cancelled_at is not None
